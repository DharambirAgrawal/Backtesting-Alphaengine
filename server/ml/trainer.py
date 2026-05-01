from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from statistics import fmean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ModelRegistry
from core.supabase_client import supabase_storage
from data.exceptions import MarketDataUnavailableError
from data.market_data import get_history, get_ohlcv_dataframe
from ml.features import add_technical_features
from ml.model_fit import fit_lstm_price_direction, fit_xgb_direction
from ml.predictor import invalidate_model_cache


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _features_from_history_rows(rows: list[dict]):
    import pandas as pd

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame()

    frame["date"] = pd.to_datetime(frame.get("date"), errors="coerce", utc=True)
    frame = frame.dropna(subset=["date"]).set_index("date").sort_index()

    for col in ["open", "high", "low", "close", "volume"]:
        frame[col] = pd.to_numeric(frame.get(col), errors="coerce")

    frame = frame.dropna(subset=["close", "volume"])
    return add_technical_features(frame)


async def _upsert_model(
    db: AsyncSession,
    ticker: str,
    model_type: str,
    accuracy: float,
    training_rows: int,
    supabase_path: str,
) -> ModelRegistry:
    stmt = select(ModelRegistry).where(
        ModelRegistry.ticker == ticker,
        ModelRegistry.model_type == model_type,
    )
    existing = await db.scalar(stmt)

    if existing:
        existing.accuracy = accuracy
        existing.training_rows = training_rows
        existing.trained_at = datetime.now(timezone.utc)
        existing.supabase_path = supabase_path
        existing.is_active = True
        return existing

    item = ModelRegistry(
        ticker=ticker,
        model_type=model_type,
        accuracy=accuracy,
        training_rows=training_rows,
        trained_at=datetime.now(timezone.utc),
        supabase_path=supabase_path,
        is_active=True,
    )
    db.add(item)
    return item


async def train_ticker_models(db: AsyncSession, ticker: str) -> dict:
    symbol = ticker.upper()
    try:
        df = await get_ohlcv_dataframe(symbol, period="5y")
        features = add_technical_features(df)

        if features.empty:
            history_rows = await get_history(symbol, days=756)
            features = _features_from_history_rows(history_rows)
    except MarketDataUnavailableError as exc:
        raise ValueError(str(exc)) from exc

    if features.empty:
        raise ValueError(f"Not enough historical data to train models for {symbol}")

    training_rows = int(len(features))

    lstm_path = f"lstm/{symbol}_lstm.pt"
    xgb_path = f"xgboost/{symbol}_xgb.pkl"

    xgb_pack, xgb_acc = await asyncio.to_thread(fit_xgb_direction, features)
    lstm_pack, lstm_acc = await asyncio.to_thread(fit_lstm_price_direction, features)

    supabase_storage.upload_bytes(
        xgb_path,
        xgb_pack["bytes"],
        content_type="application/octet-stream",
    )
    supabase_storage.upload_bytes(
        lstm_path,
        lstm_pack["bytes"],
        content_type="application/octet-stream",
    )

    await _upsert_model(
        db,
        symbol,
        "xgboost",
        _clamp(xgb_acc),
        training_rows,
        xgb_path,
    )
    await _upsert_model(
        db,
        symbol,
        "lstm",
        _clamp(lstm_acc),
        training_rows,
        lstm_path,
    )

    await db.commit()
    invalidate_model_cache(symbol)

    return {
        "ticker": symbol,
        "training_rows": training_rows,
        "models": {
            "lstm": round(float(lstm_acc), 4),
            "xgboost": round(float(xgb_acc), 4),
        },
    }


async def train_many_tickers(db: AsyncSession, tickers: list[str]) -> dict:
    results: list[dict] = []
    failed: list[dict] = []

    for ticker in sorted({item.upper() for item in tickers if item}):
        try:
            result = await train_ticker_models(db, ticker)
            results.append(result)
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})
            
        # Increase delay to 15s to respect Alpha Vantage's free tier limit (5 requests per minute)
        # This ensures that even with 20+ tickers, we don't get blocked.
        await asyncio.sleep(15.0)

    avg_accuracy = 0.0
    if results:
        all_scores: list[float] = []
        for result in results:
            all_scores.extend(result["models"].values())
        avg_accuracy = fmean(all_scores)

    return {
        "trained": results,
        "failed": failed,
        "average_accuracy": round(avg_accuracy, 4) if results else 0.0,
    }
