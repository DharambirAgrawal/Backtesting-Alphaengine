from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from api.utils import as_float
from core.database import get_db
from core.models import ModelRegistry, PortfolioTicker, User
from core.schemas import MessageResponse, ModelAccuracyOut, ModelOut
from ml.evaluator import get_accuracy_series
from ml.trainer import train_many_tickers, train_ticker_models

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelOut])
async def list_models(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ModelRegistry).order_by(
        ModelRegistry.ticker.asc(),
        ModelRegistry.model_type.asc(),
    )
    rows = (await db.scalars(stmt)).all()

    output: list[ModelOut] = []
    for row in rows:
        model_type = row.model_type.lower().strip()
        if model_type not in {"lstm", "xgboost"}:
            continue
        output.append(
            ModelOut(
                id=row.id,
                ticker=row.ticker,
                model_type=model_type,
                accuracy=as_float(row.accuracy),
                training_rows=row.training_rows or 0,
                trained_at=row.trained_at,
                is_active=row.is_active,
            )
        )
    return output


@router.post("/models/train/{ticker}", response_model=MessageResponse)
async def train_model(
    ticker: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await train_ticker_models(db, ticker.upper())
    return MessageResponse(message=f"Training started for {ticker.upper()}")


@router.post("/models/retrain-all", response_model=MessageResponse)
async def retrain_all_models(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PortfolioTicker.ticker).distinct()
    tickers = [str(item).upper() for item in (await db.scalars(stmt)).all()]

    if tickers:
        await train_many_tickers(db, tickers)

    return MessageResponse(message=f"Retraining requested for {len(tickers)} ticker(s)")


@router.get("/models/{ticker}/accuracy", response_model=ModelAccuracyOut)
async def get_model_accuracy(
    ticker: str,
    model_type: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized = model_type.lower().strip() if model_type else None
    if normalized and normalized not in {"lstm", "xgboost"}:
        normalized = None

    payload = await get_accuracy_series(
        db=db,
        ticker=ticker.upper(),
        model_type=normalized,
        limit=180,
    )
    return ModelAccuracyOut(**payload)
