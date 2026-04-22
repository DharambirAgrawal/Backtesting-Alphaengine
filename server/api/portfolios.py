from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_portfolio_or_404
from api.utils import build_portfolio_out, get_portfolio_tickers, normalize_ticker, snapshot_portfolio
from core.database import SessionLocal, get_db
from core.models import (
    AgentRun,
    Holding,
    ModelRegistry,
    Portfolio,
    PortfolioSnapshot,
    PortfolioTicker,
    PredictionHistory,
    Transaction,
    User,
)
from core.schemas import (
    AddTickersRequest,
    MessageResponse,
    PortfolioCreateRequest,
    PortfolioOut,
    PortfolioUpdateRequest,
)
from core.supabase_client import supabase_storage
from data.ticker_search import validate_ticker
from ml.trainer import train_many_tickers

router = APIRouter(tags=["portfolios"])
_background_train_semaphore = asyncio.Semaphore(1)


async def _train_tickers_background(tickers: list[str]) -> None:
    if not tickers:
        return

    async with _background_train_semaphore:
        async with SessionLocal() as db:
            await train_many_tickers(db, tickers)


async def _cleanup_orphaned_model_data(
    db: AsyncSession,
    tickers: list[str],
) -> None:
    if not tickers:
        return

    normalized = sorted({normalize_ticker(ticker) for ticker in tickers if ticker})
    remaining_stmt = select(PortfolioTicker.ticker).where(PortfolioTicker.ticker.in_(normalized))
    remaining = {str(item).upper() for item in (await db.scalars(remaining_stmt)).all()}
    orphaned = [ticker for ticker in normalized if ticker not in remaining]

    if not orphaned:
        return

    model_rows = (
        await db.scalars(select(ModelRegistry).where(ModelRegistry.ticker.in_(orphaned)))
    ).all()
    storage_paths = [row.supabase_path for row in model_rows if row.supabase_path]
    for row in model_rows:
        await db.delete(row)

    history_rows = (
        await db.scalars(select(PredictionHistory).where(PredictionHistory.ticker.in_(orphaned)))
    ).all()
    for row in history_rows:
        await db.delete(row)

    await db.commit()

    if storage_paths:
        supabase_storage.remove(storage_paths)


async def _delete_portfolio_children(db: AsyncSession, portfolio_id: str) -> None:
    # Explicit child cleanup protects deletes when deployed DB constraints drift
    # from SQLAlchemy model definitions (for example, legacy FKs without CASCADE).
    await db.execute(delete(Transaction).where(Transaction.portfolio_id == portfolio_id))
    await db.execute(delete(Holding).where(Holding.portfolio_id == portfolio_id))
    await db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id))
    await db.execute(delete(AgentRun).where(AgentRun.portfolio_id == portfolio_id))
    await db.execute(delete(PortfolioTicker).where(PortfolioTicker.portfolio_id == portfolio_id))


@router.get("/portfolios", response_model=list[PortfolioOut])
async def list_portfolios(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Portfolio).order_by(Portfolio.created_at.desc())
    rows = (await db.scalars(stmt)).all()
    return [await build_portfolio_out(db, row) for row in rows]


@router.post("/portfolios", response_model=PortfolioOut)
async def create_portfolio(
    payload: PortfolioCreateRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = Portfolio(
        name=payload.name.strip(),
        description=payload.description,
        starting_capital=round(payload.starting_capital, 2),
        current_cash=round(payload.starting_capital, 2),
        is_active=True,
    )
    db.add(portfolio)
    await db.flush()

    normalized_tickers: list[str] = []
    seen = set()
    for ticker in payload.tickers:
        symbol = normalize_ticker(ticker)
        if not symbol or symbol in seen:
            continue
        if not await validate_ticker(symbol):
            continue
        seen.add(symbol)
        normalized_tickers.append(symbol)

        db.add(PortfolioTicker(portfolio_id=portfolio.id, ticker=symbol))
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                ticker=symbol,
                shares=0,
                avg_buy_price=None,
            )
        )

    await db.commit()
    await snapshot_portfolio(db, portfolio.id)

    if normalized_tickers:
        asyncio.create_task(_train_tickers_background(normalized_tickers))

    refreshed = await db.get(Portfolio, portfolio.id)
    if not refreshed:
        raise HTTPException(status_code=500, detail="Failed to create portfolio")

    return await build_portfolio_out(db, refreshed)


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioOut)
async def get_portfolio(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    return await build_portfolio_out(db, portfolio)


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioOut)
async def update_portfolio(
    portfolio_id: str,
    payload: PortfolioUpdateRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)

    if payload.name is not None:
        portfolio.name = payload.name.strip()
    if payload.description is not None:
        portfolio.description = payload.description
    if payload.is_active is not None:
        portfolio.is_active = payload.is_active

    await db.commit()
    await db.refresh(portfolio)

    return await build_portfolio_out(db, portfolio)


@router.delete("/portfolios/{portfolio_id}", response_model=MessageResponse)
async def delete_portfolio(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    tracked_tickers = await get_portfolio_tickers(db, portfolio.id)
    await _delete_portfolio_children(db, str(portfolio.id))
    await db.delete(portfolio)
    await db.commit()
    await _cleanup_orphaned_model_data(db, tracked_tickers)
    return MessageResponse(message="Portfolio deleted")


@router.post("/portfolios/{portfolio_id}/tickers", response_model=MessageResponse)
async def add_tickers(
    portfolio_id: str,
    payload: AddTickersRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)

    existing = set(await get_portfolio_tickers(db, portfolio.id))
    to_add: list[str] = []
    invalid: list[str] = []

    for raw in payload.tickers:
        symbol = normalize_ticker(raw)
        if not symbol or symbol in existing:
            continue
        if not await validate_ticker(symbol):
            invalid.append(symbol)
            continue
        existing.add(symbol)
        to_add.append(symbol)

        db.add(PortfolioTicker(portfolio_id=portfolio.id, ticker=symbol))

        holding_exists = await db.scalar(
            select(Holding).where(
                Holding.portfolio_id == portfolio.id,
                Holding.ticker == symbol,
            )
        )
        if not holding_exists:
            db.add(
                Holding(
                    portfolio_id=portfolio.id,
                    ticker=symbol,
                    shares=0,
                    avg_buy_price=None,
                )
            )

    await db.commit()

    if to_add:
        asyncio.create_task(_train_tickers_background(to_add))

    if invalid:
        return MessageResponse(
            message=f"Added {len(to_add)} ticker(s). Skipped invalid symbols: {', '.join(sorted(set(invalid)))}"
        )
    return MessageResponse(message=f"Added {len(to_add)} ticker(s)")


@router.delete("/portfolios/{portfolio_id}/tickers/{ticker}", response_model=MessageResponse)
async def remove_ticker(
    portfolio_id: str,
    ticker: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    symbol = normalize_ticker(ticker)

    ticker_row = await db.scalar(
        select(PortfolioTicker).where(
            PortfolioTicker.portfolio_id == portfolio.id,
            PortfolioTicker.ticker == symbol,
        )
    )

    if not ticker_row:
        raise HTTPException(status_code=404, detail="Ticker not found in portfolio")

    holding = await db.scalar(
        select(Holding).where(Holding.portfolio_id == portfolio.id, Holding.ticker == symbol)
    )
    if holding and float(holding.shares or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove {symbol} while shares are still held",
        )

    await db.delete(ticker_row)

    if holding:
        await db.delete(holding)

    await db.commit()
    await _cleanup_orphaned_model_data(db, [symbol])

    return MessageResponse(message=f"Ticker {symbol} removed")


@router.get("/portfolios/{portfolio_id}/tickers", response_model=list[str])
async def list_tickers(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    return await get_portfolio_tickers(db, portfolio.id)
