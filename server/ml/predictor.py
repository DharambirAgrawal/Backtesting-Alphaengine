from __future__ import annotations

import io
import math
from collections import OrderedDict
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch

from core.supabase_client import supabase_storage
from data.market_data import get_current_price, get_history, get_ohlcv_dataframe
from ml.features import add_technical_features
from ml.model_fit import TinyLSTM


MODEL_CACHE_MAX_ITEMS = 16
MODEL_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _cache_key(ticker: str, kind: str) -> str:
    return f"{ticker.upper()}:{kind}"


def _cache_get(key: str) -> dict[str, Any] | None:
    item = MODEL_CACHE.get(key)
    if item is None:
        return None
    MODEL_CACHE.move_to_end(key)
    return item


def _cache_set(key: str, value: dict[str, Any]) -> None:
    MODEL_CACHE[key] = value
    MODEL_CACHE.move_to_end(key)
    while len(MODEL_CACHE) > MODEL_CACHE_MAX_ITEMS:
        MODEL_CACHE.popitem(last=False)


def invalidate_model_cache(ticker: str) -> None:
    symbol = ticker.upper()
    MODEL_CACHE.pop(_cache_key(symbol, "xgb"), None)
    MODEL_CACHE.pop(_cache_key(symbol, "lstm"), None)


def _load_xgb_bundle(ticker: str) -> dict[str, Any] | None:
    key = _cache_key(ticker, "xgb")
    cached = _cache_get(key)
    if cached is not None:
        return cached

    raw = supabase_storage.download_bytes(f"xgboost/{ticker.upper()}_xgb.pkl")
    if not raw:
        return None
    try:
        bundle = joblib.load(io.BytesIO(raw))
        if not isinstance(bundle, dict) or "model" not in bundle:
            return None
        _cache_set(key, bundle)
        return bundle
    except Exception:
        return None


def _load_lstm_bundle(ticker: str) -> dict[str, Any] | None:
    key = _cache_key(ticker, "lstm")
    cached = _cache_get(key)
    if cached is not None:
        return cached

    raw = supabase_storage.download_bytes(f"lstm/{ticker.upper()}_lstm.pt")
    if not raw:
        return None
    try:
        raw_io = io.BytesIO(raw)
        try:
            payload = torch.load(raw_io, map_location=torch.device("cpu"), weights_only=False)
        except TypeError:
            raw_io.seek(0)
            payload = torch.load(raw_io, map_location=torch.device("cpu"))
        if not isinstance(payload, dict) or "state_dict" not in payload:
            return None
        _cache_set(key, payload)
        return payload
    except Exception:
        return None


async def _latest_features_row(ticker: str) -> tuple[pd.DataFrame, pd.Series | None]:
    df = await get_ohlcv_dataframe(ticker, period="2y")
    feats = add_technical_features(df)
    if feats.empty:
        rows = await get_history(ticker, days=260)
        feats = add_technical_features(_df_from_history_rows(rows))
    if feats.empty:
        return feats, None
    return feats, feats.iloc[-1]


def _df_from_history_rows(rows: list[dict]) -> pd.DataFrame:
    import pandas as pd

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame.get("date"), errors="coerce", utc=True)
    frame = frame.dropna(subset=["date"]).set_index("date").sort_index()
    for col in ["open", "high", "low", "close", "volume"]:
        frame[col] = pd.to_numeric(frame.get(col), errors="coerce")
    frame = frame.dropna(subset=["close", "volume"])
    return frame


async def predict_price(ticker: str, horizon_days: int = 3) -> dict:
    symbol = ticker.upper()
    lstm = _load_lstm_bundle(symbol)

    feats, latest = await _latest_features_row(symbol)
    current = await get_current_price(symbol)

    if lstm and latest is not None and not feats.empty:
        try:
            cols = lstm["feature_cols"]
            seq_len = int(lstm["seq_len"])
            mean = np.asarray(lstm["mean"], dtype=np.float64)
            std = np.asarray(lstm["std"], dtype=np.float64)
            mat = feats[cols].astype(np.float64).replace([np.inf, -np.inf], np.nan).fillna(0.0).values
            if len(mat) >= seq_len:
                window = (mat[-seq_len:] - mean) / std
                xt = torch.from_numpy(window.reshape(1, seq_len, -1).astype(np.float32))
                net = TinyLSTM(input_dim=int(lstm["input_dim"]), hidden=int(lstm.get("hidden", 36)), num_layers=1)
                net.load_state_dict(lstm["state_dict"])
                net.eval()
                with torch.no_grad():
                    next_ret = float(net(xt).numpy().flatten()[0])
                projected = current * math.pow(max(1e-9, 1.0 + next_ret), max(1, horizon_days))
                vol = float(np.std(np.diff(feats["close"].tail(40).astype(float))) / max(current, 1e-9))
                confidence = max(0.2, min(0.95, 1.0 - min(vol * 12, 0.85)))
                return {
                    "ticker": symbol,
                    "horizon_days": horizon_days,
                    "predicted_price": round(float(projected), 4),
                    "confidence": round(float(confidence), 4),
                }
        except Exception:
            pass

    bars = await get_history(symbol, days=120)
    closes = np.array([float(item["close"]) for item in bars], dtype=float)

    if closes.size < 5:
        return {
            "ticker": symbol,
            "horizon_days": horizon_days,
            "predicted_price": round(float(current), 4),
            "confidence": 0.5,
        }

    daily_returns = np.diff(closes) / closes[:-1]
    lookback = min(20, daily_returns.size)
    mean_return = float(np.mean(daily_returns[-lookback:]))
    volatility = float(np.std(daily_returns[-lookback:]))
    projected = current * math.pow(1 + mean_return, max(1, horizon_days))
    confidence = max(0.2, min(0.95, 1.0 - (volatility * 12)))

    return {
        "ticker": symbol,
        "horizon_days": horizon_days,
        "predicted_price": round(float(projected), 4),
        "confidence": round(float(confidence), 4),
    }


async def classify_direction(ticker: str) -> dict:
    symbol = ticker.upper()
    bundle = _load_xgb_bundle(symbol)
    feats, latest = await _latest_features_row(symbol)
    current = await get_current_price(symbol)

    if bundle and latest is not None:
        try:
            cols = bundle["feature_cols"]
            row = latest[list(cols)].astype(np.float64).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            X = row.values.reshape(1, -1)
            clf = bundle["model"]
            if hasattr(clf, "predict_proba"):
                prob_up = float(clf.predict_proba(X)[0][1])
            else:
                prob_up = 0.55
            direction = "UP" if prob_up >= 0.5 else "DOWN"
            probability = prob_up if direction == "UP" else (1.0 - prob_up)
            return {
                "ticker": symbol,
                "direction": direction,
                "probability": round(min(max(probability, 0.0), 1.0), 4),
            }
        except Exception:
            pass

    prediction = await predict_price(symbol, horizon_days=3)
    predicted = float(prediction["predicted_price"])
    confidence = float(prediction["confidence"])

    direction = "UP" if predicted >= current else "DOWN"
    probability = confidence if direction == "UP" else max(0.5, confidence - 0.1)

    return {
        "ticker": symbol,
        "direction": direction,
        "probability": round(min(max(probability, 0.0), 1.0), 4),
    }
