from __future__ import annotations

import numpy as np
import pandas as pd

from data.market_data import get_ohlcv_dataframe


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    frame = df.copy()

    required = {"close", "volume"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()

    try:
        import ta

        frame["rsi"] = ta.momentum.RSIIndicator(frame["close"], window=14).rsi()
        macd = ta.trend.MACD(frame["close"])
        frame["macd"] = macd.macd()
        frame["macd_signal"] = macd.macd_signal()

        bbands = ta.volatility.BollingerBands(frame["close"], window=20, window_dev=2)
        frame["bb_low"] = bbands.bollinger_lband()
        frame["bb_high"] = bbands.bollinger_hband()
    except Exception:
        delta = frame["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        frame["rsi"] = 100 - (100 / (1 + rs))

        frame["macd"] = frame["close"].ewm(span=12, adjust=False).mean() - frame[
            "close"
        ].ewm(span=26, adjust=False).mean()
        frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False).mean()

        rolling = frame["close"].rolling(20)
        middle = rolling.mean()
        std = rolling.std()
        frame["bb_low"] = middle - (2 * std)
        frame["bb_high"] = middle + (2 * std)

    frame["bb_position"] = (frame["close"] - frame["bb_low"]) / (
        (frame["bb_high"] - frame["bb_low"]).replace(0, np.nan)
    )
    frame["volume_ratio"] = frame["volume"] / frame["volume"].rolling(20).mean()
    frame["return_5d"] = frame["close"].pct_change(5)
    frame["return_10d"] = frame["close"].pct_change(10)
    frame["return_20d"] = frame["close"].pct_change(20)

    if isinstance(frame.index, pd.DatetimeIndex):
        frame["day_of_week"] = frame.index.dayofweek
    else:
        frame["day_of_week"] = 0

    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    return frame


async def get_technical_signals(ticker: str) -> dict:
    df = await get_ohlcv_dataframe(ticker, period="6mo")
    features = add_technical_features(df)

    if features.empty:
        return {
            "rsi": 50.0,
            "macd": "neutral",
            "bb_position": 0.5,
        }

    latest = features.iloc[-1]

    macd_value = float(latest.get("macd", 0.0))
    macd_signal = float(latest.get("macd_signal", 0.0))
    if macd_value > macd_signal:
        macd_trend = "bullish_cross"
    elif macd_value < macd_signal:
        macd_trend = "bearish_cross"
    else:
        macd_trend = "neutral"

    return {
        "rsi": round(float(latest.get("rsi", 50.0)), 2),
        "macd": macd_trend,
        "bb_position": round(float(latest.get("bb_position", 0.5)), 4),
    }
