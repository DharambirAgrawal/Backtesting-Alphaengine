from __future__ import annotations

import math

import numpy as np

from data.market_data import get_current_price, get_history

MODEL_CACHE: dict[str, dict] = {}


async def predict_price(ticker: str, horizon_days: int = 3) -> dict:
    bars = await get_history(ticker, days=120)
    closes = np.array([float(item["close"]) for item in bars], dtype=float)

    if closes.size < 5:
        current = await get_current_price(ticker)
        return {
            "ticker": ticker.upper(),
            "horizon_days": horizon_days,
            "predicted_price": round(current, 4),
            "confidence": 0.5,
        }

    current = closes[-1]
    daily_returns = np.diff(closes) / closes[:-1]

    lookback = min(20, daily_returns.size)
    mean_return = float(np.mean(daily_returns[-lookback:]))
    volatility = float(np.std(daily_returns[-lookback:]))

    projected = current * math.pow(1 + mean_return, max(1, horizon_days))
    confidence = max(0.2, min(0.95, 1.0 - (volatility * 12)))

    return {
        "ticker": ticker.upper(),
        "horizon_days": horizon_days,
        "predicted_price": round(float(projected), 4),
        "confidence": round(float(confidence), 4),
    }


async def classify_direction(ticker: str) -> dict:
    prediction = await predict_price(ticker, horizon_days=3)
    current = await get_current_price(ticker)
    predicted = float(prediction["predicted_price"])
    confidence = float(prediction["confidence"])

    direction = "UP" if predicted >= current else "DOWN"
    probability = confidence if direction == "UP" else max(0.5, confidence - 0.1)

    return {
        "ticker": ticker.upper(),
        "direction": direction,
        "probability": round(min(max(probability, 0.0), 1.0), 4),
    }
