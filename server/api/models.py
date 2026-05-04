from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_portfolio_or_404
from api.utils import as_float
from core.config import settings
from core.database import SessionLocal, get_db
from core.models import ModelRegistry, Portfolio, PortfolioTicker, User
from core.schemas import (
    MessageResponse,
    ModelAccuracyOut,
    ModelCoverageTickerOut,
    ModelRetrainAllOut,
    ModelOut,
    ModelOverviewOut,
    ModelOverviewSummaryOut,
    ModelPortfolioReferenceOut,
)
from ml.evaluator import get_accuracy_series, get_latest_forward_accuracy
from ml.trainer import get_training_errors, train_many_tickers, train_ticker_models

router = APIRouter(tags=["models"])
MODEL_TYPES = ("lstm", "xgboost")
_background_train_semaphore = asyncio.Semaphore(1)


async def _train_ticker_background(ticker: str) -> None:
    async with _background_train_semaphore:
        async with SessionLocal() as db:
            try:
                await train_ticker_models(db, ticker)
            except Exception as exc:
                logging.exception("Model training failed for %s: %s", ticker, exc)


async def _train_many_background(tickers: list[str]) -> None:
    if not tickers:
        return
    async with _background_train_semaphore:
        async with SessionLocal() as db:
            try:
                await train_many_tickers(db, tickers)
            except Exception as exc:
                logging.exception("Bulk model retrain failed: %s", exc)


def _normalize_model_type(value: str) -> str | None:
    normalized = value.lower().strip()
    if normalized in MODEL_TYPES:
        return normalized
    return None


async def _get_scoped_tickers(
    db: AsyncSession,
    request: Request,
    portfolio_id: str | None = None,
) -> list[str]:
    stmt = select(PortfolioTicker.ticker).distinct()

    if portfolio_id:
        portfolio = await get_portfolio_or_404(portfolio_id, request, db)
        stmt = stmt.where(PortfolioTicker.portfolio_id == portfolio.id)

    tickers = [str(item).upper() for item in (await db.scalars(stmt)).all()]
    return sorted(set(tickers))


@router.get("/models", response_model=list[ModelOut])
async def list_models(
    request: Request,
    portfolio_id: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ModelRegistry)

    if portfolio_id:
        tickers = await _get_scoped_tickers(db, request, portfolio_id)
        if not tickers:
            return []
        stmt = stmt.where(ModelRegistry.ticker.in_(tickers))

    stmt = stmt.order_by(
        ModelRegistry.ticker.asc(),
        ModelRegistry.model_type.asc(),
    )
    rows = (await db.scalars(stmt)).all()

    output: list[ModelOut] = []
    for row in rows:
        model_type = row.model_type.lower().strip()
        if model_type not in {"lstm", "xgboost"}:
            continue
        accuracy = as_float(row.accuracy)
        forward_accuracy = None
        if model_type == "lstm":
            forward_accuracy = await get_latest_forward_accuracy(
                db,
                ticker=row.ticker,
                model_type=model_type,
            )
        output.append(
            ModelOut(
                id=row.id,
                ticker=row.ticker,
                model_type=model_type,
                accuracy=forward_accuracy if forward_accuracy is not None else accuracy,
                training_rows=row.training_rows or 0,
                trained_at=row.trained_at,
                is_active=row.is_active,
            )
        )
    return output


@router.get("/models/overview", response_model=ModelOverviewOut)
async def get_models_overview(
    request: Request,
    portfolio_id: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticker_stmt = (
        select(
            PortfolioTicker.ticker,
            Portfolio.id,
            Portfolio.name,
            Portfolio.is_active,
        )
        .join(Portfolio, Portfolio.id == PortfolioTicker.portfolio_id)
        .order_by(PortfolioTicker.ticker.asc(), Portfolio.name.asc())
    )

    if portfolio_id:
        portfolio = await get_portfolio_or_404(portfolio_id, request, db)
        ticker_stmt = ticker_stmt.where(PortfolioTicker.portfolio_id == portfolio.id)

    ticker_rows = (await db.execute(ticker_stmt)).all()
    if not ticker_rows:
        return ModelOverviewOut(
            summary=ModelOverviewSummaryOut(
                tracked_tickers=0,
                referenced_portfolios=0,
                trained_model_count=0,
                fully_trained_tickers=0,
                missing_model_count=0,
            ),
            available_model_types=list(MODEL_TYPES),
            coverage=[],
        )

    scoped_tickers: set[str] = set()
    portfolio_ids: set[str] = set()
    coverage_map: dict[str, list[ModelPortfolioReferenceOut]] = {}

    for ticker, ref_id, name, is_active in ticker_rows:
        symbol = str(ticker).upper()
        scoped_tickers.add(symbol)
        portfolio_ids.add(str(ref_id))
        coverage_map.setdefault(symbol, []).append(
            ModelPortfolioReferenceOut(
                id=ref_id,
                name=name,
                is_active=bool(is_active),
            )
        )

    model_stmt = (
        select(ModelRegistry)
        .where(ModelRegistry.ticker.in_(sorted(scoped_tickers)))
        .order_by(ModelRegistry.ticker.asc(), ModelRegistry.model_type.asc())
    )
    model_rows = (await db.scalars(model_stmt)).all()

    models_by_ticker: dict[str, list[ModelRegistry]] = {}
    for row in model_rows:
        model_type = _normalize_model_type(row.model_type)
        if not model_type or not row.is_active:
            continue
        models_by_ticker.setdefault(row.ticker.upper(), []).append(row)

    coverage: list[ModelCoverageTickerOut] = []
    trained_model_count = 0
    fully_trained_tickers = 0
    missing_model_count = 0
    training_errors = get_training_errors()

    for ticker in sorted(scoped_tickers):
        rows = models_by_ticker.get(ticker, [])
        trained_types = [
            model_type
            for model_type in MODEL_TYPES
            if any(_normalize_model_type(row.model_type) == model_type for row in rows)
        ]
        missing_types = [
            model_type for model_type in MODEL_TYPES if model_type not in trained_types
        ]
        last_trained_at = max((row.trained_at for row in rows), default=None)

        trained_model_count += len(trained_types)
        missing_model_count += len(missing_types)
        if not missing_types:
            fully_trained_tickers += 1

        coverage.append(
            ModelCoverageTickerOut(
                ticker=ticker,
                portfolios=coverage_map.get(ticker, []),
                trained_model_types=trained_types,
                missing_model_types=missing_types,
                coverage_pct=round((len(trained_types) / len(MODEL_TYPES)) * 100, 2),
                is_fully_trained=not missing_types,
                last_trained_at=last_trained_at,
                last_training_error=training_errors.get(ticker),
            )
        )

    return ModelOverviewOut(
        summary=ModelOverviewSummaryOut(
            tracked_tickers=len(scoped_tickers),
            referenced_portfolios=len(portfolio_ids),
            trained_model_count=trained_model_count,
            fully_trained_tickers=fully_trained_tickers,
            missing_model_count=missing_model_count,
        ),
        available_model_types=list(MODEL_TYPES),
        coverage=coverage,
    )


@router.post("/models/train/{ticker}", response_model=MessageResponse)
async def train_model(
    ticker: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    symbol = ticker.upper().strip()
    if not symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticker is required",
        )
    if settings.is_production:
        # Run training in the background so the request does not time out on hosted deployments.
        asyncio.create_task(_train_ticker_background(symbol))
        return MessageResponse(message=f"Training started for {symbol}")

    try:
        await train_ticker_models(db, symbol)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message=f"Training completed for {symbol}")


@router.post("/models/retrain-all", response_model=ModelRetrainAllOut)
async def retrain_all_models(
    request: Request,
    portfolio_id: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tickers = await _get_scoped_tickers(db, request, portfolio_id)

    if settings.is_production:
        # Schedule long-running retraining in the background to avoid request timeouts.
        asyncio.create_task(_train_many_background(tickers))

        scope = "portfolio" if portfolio_id else "tracked"
        message = (
            f"Retraining queued for {len(tickers)} {scope} ticker(s). "
            "Check back shortly for updated models."
        )
        return ModelRetrainAllOut(
            message=message,
            total_tickers=len(tickers),
            trained_count=0,
            failed_count=0,
            failed=[],
        )

    trained_count = 0
    failed: list[dict] = []
    if tickers:
        result = await train_many_tickers(db, tickers)
        trained_count = len(result.get("trained", []))
        failed = result.get("failed", [])

    scope = "portfolio" if portfolio_id else "tracked"
    failed_count = len(failed)
    message = (
        f"Retraining finished for {len(tickers)} {scope} ticker(s): "
        f"{trained_count} succeeded, {failed_count} failed"
    )
    return ModelRetrainAllOut(
        message=message,
        total_tickers=len(tickers),
        trained_count=trained_count,
        failed_count=failed_count,
        failed=failed,
    )


@router.get("/models/{ticker}/accuracy", response_model=ModelAccuracyOut)
async def get_model_accuracy(
    ticker: str,
    request: Request,
    model_type: str | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized = model_type.lower().strip() if model_type else None
    if normalized and normalized not in MODEL_TYPES:
        normalized = None

    payload = await get_accuracy_series(
        db=db,
        ticker=ticker.upper(),
        model_type=normalized,
        limit=180,
    )
    return ModelAccuracyOut(**payload)
