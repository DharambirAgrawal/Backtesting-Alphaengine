from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import PredictionHistory


def _point_accuracy(predicted: float, actual: float) -> float:
    if actual == 0:
        return 0.0
    error = abs(predicted - actual) / abs(actual)
    return max(0.0, min(1.0, 1.0 - error))


def _rolling_average(values: list[float], window: int = 7) -> list[float]:
    if not values:
        return []

    rolling: list[float] = []
    for idx in range(len(values)):
        start = max(0, idx - window + 1)
        subset = values[start : idx + 1]
        rolling.append(sum(subset) / len(subset))
    return rolling


async def record_prediction(
    db: AsyncSession,
    ticker: str,
    model_type: str,
    predicted_price: float,
    actual_price: float | None,
    prediction_date: date | None = None,
    prediction_for_date: date | None = None,
) -> PredictionHistory:
    row = PredictionHistory(
        ticker=ticker.upper(),
        model_type=model_type,
        predicted_price=predicted_price,
        actual_price=actual_price,
        prediction_date=prediction_date or datetime.now(timezone.utc).date(),
        prediction_for_date=prediction_for_date,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_accuracy_series(
    db: AsyncSession,
    ticker: str,
    model_type: str | None = None,
    limit: int = 180,
) -> dict:
    stmt = select(PredictionHistory).where(PredictionHistory.ticker == ticker.upper())
    if model_type:
        stmt = stmt.where(PredictionHistory.model_type == model_type)

    stmt = stmt.order_by(
        desc(PredictionHistory.prediction_for_date),
        desc(PredictionHistory.prediction_date),
        desc(PredictionHistory.recorded_at),
    ).limit(limit)
    rows = list(reversed((await db.scalars(stmt)).all()))

    dates: list[str] = []
    predicted: list[float] = []
    actual: list[float] = []

    for row in rows:
        predicted_value = float(row.predicted_price) if row.predicted_price is not None else None
        actual_value = float(row.actual_price) if row.actual_price is not None else None
        if predicted_value is None or actual_value is None or actual_value == 0:
            continue

        resolved_date = row.prediction_for_date or row.prediction_date or row.recorded_at.date()
        dt = resolved_date.isoformat()
        dates.append(dt)
        predicted.append(predicted_value)
        actual.append(actual_value)

    point_scores = [_point_accuracy(p, a) for p, a in zip(predicted, actual)]
    rolling_accuracy = _rolling_average(point_scores, window=7) if point_scores else []

    return {
        "dates": dates,
        "predicted": predicted,
        "actual": actual,
        "rolling_accuracy": rolling_accuracy,
    }


async def should_trigger_retrain(
    db: AsyncSession,
    ticker: str,
    model_type: str | None = None,
    threshold: float = 0.52,
) -> bool:
    series = await get_accuracy_series(db, ticker=ticker, model_type=model_type, limit=30)
    rolling = series.get("rolling_accuracy") or []
    if len(rolling) < 7:
        return False
    return float(rolling[-1]) < threshold


async def get_latest_forward_accuracy(
    db: AsyncSession,
    ticker: str,
    model_type: str | None = None,
    limit: int = 30,
) -> float | None:
    series = await get_accuracy_series(db, ticker=ticker, model_type=model_type, limit=limit)
    rolling = series.get("rolling_accuracy") or []
    if rolling:
        return float(rolling[-1])
    return None
