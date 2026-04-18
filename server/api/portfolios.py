from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_portfolio_or_404
from api.utils import build_portfolio_out, get_portfolio_tickers, normalize_ticker, snapshot_portfolio
from core.database import SessionLocal, get_db
from core.models import Holding, Portfolio, PortfolioTicker, User
from core.schemas import (
    AddTickersRequest,
    MessageResponse,
    PortfolioCreateRequest,
    PortfolioOut,
    PortfolioUpdateRequest,
)
from ml.trainer import train_many_tickers

router = APIRouter(tags=["portfolios"])


async def _train_tickers_background(tickers: list[str]) -> None:
    if not tickers:
        return

    async with SessionLocal() as db:
        await train_many_tickers(db, tickers)


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
    portfolio.is_active = False
    await db.commit()
    return MessageResponse(message="Portfolio archived")


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

    for raw in payload.tickers:
        symbol = normalize_ticker(raw)
        if not symbol or symbol in existing:
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

    await db.delete(ticker_row)

    holding = await db.scalar(
        select(Holding).where(Holding.portfolio_id == portfolio.id, Holding.ticker == symbol)
    )
    if holding and float(holding.shares or 0) <= 0:
        await db.delete(holding)

    await db.commit()

    return MessageResponse(message=f"Ticker {symbol} removed")


@router.get("/portfolios/{portfolio_id}/tickers", response_model=list[str])
async def list_tickers(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    return await get_portfolio_tickers(db, portfolio.id)
