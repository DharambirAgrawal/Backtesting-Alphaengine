from __future__ import annotations

import asyncio
import math
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    AgentRun,
    Holding,
    Portfolio,
    PortfolioSnapshot,
    PortfolioTicker,
    Transaction,
)
from core.schemas import HoldingOut, PerformanceStatsOut, PortfolioOut, TransactionOut
from data.exceptions import MarketDataUnavailableError
from data.market_data import get_current_price


def normalize_ticker(value: str) -> str:
    return value.strip().upper()


def as_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


async def heal_stale_agent_runs(
    db: AsyncSession,
    *,
    portfolio_id=None,
    stale_after_minutes: int = 60,
) -> int:
    """Mark long-running agent runs as failed so they don't block new runs.

    This primarily defends against crashes/lock contention bugs that leave rows in
    a perpetual "running" state.
    """

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
    stmt = (
        select(AgentRun)
        .where(AgentRun.status == "running")
        .where(AgentRun.completed_at.is_(None))
        .where(AgentRun.started_at < cutoff)
        .order_by(AgentRun.started_at.asc())
    )
    if portfolio_id is not None:
        stmt = stmt.where(AgentRun.portfolio_id == portfolio_id)

    stale_runs = list((await db.scalars(stmt)).all())
    if not stale_runs:
        return 0

    now = datetime.now(timezone.utc)
    for run in stale_runs:
        run.status = "failed"
        if not (run.summary or "").strip():
            run.summary = "Run marked failed: stale running state."
        run.completed_at = now

    await db.commit()
    return len(stale_runs)


async def get_portfolio_tickers(db: AsyncSession, portfolio_id) -> list[str]:
    stmt = (
        select(PortfolioTicker.ticker)
        .where(PortfolioTicker.portfolio_id == portfolio_id)
        .order_by(PortfolioTicker.ticker.asc())
    )
    rows = (await db.scalars(stmt)).all()
    return [str(row).upper() for row in rows]


async def _price_for_holding(ticker: str, avg_buy: float) -> float:
    try:
        return await get_current_price(ticker)
    except MarketDataUnavailableError:
        return avg_buy


async def build_holdings_view(
    db: AsyncSession,
    portfolio_id,
) -> tuple[list[HoldingOut], float]:
    stmt = (
        select(Holding)
        .where(Holding.portfolio_id == portfolio_id)
        .order_by(Holding.ticker.asc())
    )
    rows = (await db.scalars(stmt)).all()

    eligible = [row for row in rows if as_float(row.shares) > 0]
    if not eligible:
        return [], 0.0

    prices = await asyncio.gather(
        *[_price_for_holding(row.ticker, as_float(row.avg_buy_price)) for row in eligible]
    )

    output: list[HoldingOut] = []
    holdings_value = 0.0

    for row, current_price in zip(eligible, prices, strict=True):
        shares = as_float(row.shares)
        avg_buy = as_float(row.avg_buy_price)
        value = shares * current_price
        cost_basis = shares * avg_buy
        profit_loss = value - cost_basis
        profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0.0

        holdings_value += value

        output.append(
            HoldingOut(
                ticker=row.ticker,
                shares=round(shares, 6),
                avg_buy_price=round(avg_buy, 4),
                current_price=round(current_price, 4),
                value=round(value, 2),
                profit_loss=round(profit_loss, 2),
                profit_loss_pct=round(profit_loss_pct, 4),
            )
        )

    return output, round(holdings_value, 2)


def _portfolio_out_from_values(
    portfolio: Portfolio,
    tickers: list[str],
    holdings_value: float,
) -> PortfolioOut:
    current_cash = as_float(portfolio.current_cash)
    starting_capital = as_float(portfolio.starting_capital)
    total_value = current_cash + holdings_value
    profit_loss = total_value - starting_capital
    profit_loss_pct = (profit_loss / starting_capital * 100) if starting_capital else 0.0

    return PortfolioOut(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        starting_capital=round(starting_capital, 2),
        current_cash=round(current_cash, 2),
        holdings_value=round(holdings_value, 2),
        total_value=round(total_value, 2),
        profit_loss=round(profit_loss, 2),
        profit_loss_pct=round(profit_loss_pct, 4),
        is_active=portfolio.is_active,
        tickers=tickers,
        created_at=portfolio.created_at,
    )


async def build_portfolio_out(db: AsyncSession, portfolio: Portfolio) -> PortfolioOut:
    tickers = await get_portfolio_tickers(db, portfolio.id)
    _, holdings_value = await build_holdings_view(db, portfolio.id)
    return _portfolio_out_from_values(portfolio, tickers, holdings_value)


def transaction_to_out(tx: Transaction) -> TransactionOut:
    return TransactionOut(
        id=tx.id,
        portfolio_id=tx.portfolio_id,
        ticker=tx.ticker,
        action=tx.action,
        shares=as_float(tx.shares),
        price_at_trade=as_float(tx.price_at_trade),
        total_value=as_float(tx.total_value),
        llm_reasoning=tx.llm_reasoning or "",
        tools_called=tx.tools_called or {},
        executed_at=tx.executed_at,
    )


async def snapshot_portfolio(db: AsyncSession, portfolio_id) -> PortfolioSnapshot:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("Portfolio not found")

    _, holdings_value = await build_holdings_view(db, portfolio_id)
    current_cash = as_float(portfolio.current_cash)
    total_value = current_cash + holdings_value

    snapshot = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        total_value=round(total_value, 2),
        cash_value=round(current_cash, 2),
        holdings_value=round(holdings_value, 2),
        snapshot_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def build_performance_stats(
    db: AsyncSession,
    portfolio_id,
    *,
    portfolio_out: PortfolioOut | None = None,
) -> PerformanceStatsOut:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("Portfolio not found")

    if portfolio_out is None:
        portfolio_out = await build_portfolio_out(db, portfolio)

    tx_stmt = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.executed_at.asc())
    )
    transactions = (await db.scalars(tx_stmt)).all()

    realized_results: list[dict] = []
    positions: dict[str, dict[str, float]] = {}

    for tx in transactions:
        ticker = tx.ticker.upper()
        action = tx.action
        shares = as_float(tx.shares)
        price = as_float(tx.price_at_trade)

        if ticker not in positions:
            positions[ticker] = {"shares": 0.0, "avg": 0.0}

        pos = positions[ticker]

        if action == "BUY":
            total_cost = (pos["shares"] * pos["avg"]) + (shares * price)
            pos["shares"] += shares
            if pos["shares"] > 0:
                pos["avg"] = total_cost / pos["shares"]

        elif action == "SELL" and pos["shares"] > 0:
            qty = min(shares, pos["shares"]) if shares > 0 else pos["shares"]
            if qty <= 0:
                continue

            gain_pct = ((price - pos["avg"]) / pos["avg"] * 100) if pos["avg"] else 0.0
            realized_results.append({"ticker": ticker, "gain_pct": gain_pct})
            pos["shares"] -= qty

    sell_trades_count = len(realized_results)
    profitable_trades = len([item for item in realized_results if item["gain_pct"] > 0])
    win_rate = profitable_trades / sell_trades_count if sell_trades_count else 0.0

    if realized_results:
        best = max(realized_results, key=lambda item: item["gain_pct"])
        worst = min(realized_results, key=lambda item: item["gain_pct"])
        best_trade = {
            "ticker": best["ticker"],
            "gain_pct": round(best["gain_pct"], 4),
        }
        worst_trade = {
            "ticker": worst["ticker"],
            "loss_pct": round(worst["gain_pct"], 4),
        }
    else:
        best_trade = {"ticker": "N/A", "gain_pct": 0.0}
        worst_trade = {"ticker": "N/A", "loss_pct": 0.0}

    snapshots_stmt = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_at.asc())
    )
    snapshots = (await db.scalars(snapshots_stmt)).all()

    values = [as_float(row.total_value) for row in snapshots if row.total_value is not None]

    max_drawdown_pct = 0.0
    if values:
        peak = values[0]
        drawdowns: list[float] = []
        for value in values:
            peak = max(peak, value)
            drawdown = ((value - peak) / peak * 100) if peak else 0.0
            drawdowns.append(drawdown)
        max_drawdown_pct = min(drawdowns)

    sharpe_ratio = 0.0
    if len(values) > 2:
        arr = np.array(values, dtype=float)
        returns = np.diff(arr) / arr[:-1]
        if returns.size > 1 and float(np.std(returns)) > 0:
            sharpe_ratio = float(np.mean(returns) / np.std(returns) * math.sqrt(252))

    return PerformanceStatsOut(
        total_return_pct=round(portfolio_out.profit_loss_pct, 4),
        sharpe_ratio=round(sharpe_ratio, 4),
        max_drawdown_pct=round(max_drawdown_pct, 4),
        win_rate=round(win_rate, 4),
        total_trades=sell_trades_count,
        profitable_trades=profitable_trades,
        best_trade=best_trade,
        worst_trade=worst_trade,
    )


async def get_recent_transactions(
    db: AsyncSession,
    portfolio_id,
    limit: int = 10,
) -> list[TransactionOut]:
    stmt = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(desc(Transaction.executed_at))
        .limit(limit)
    )
    rows = (await db.scalars(stmt)).all()
    return [transaction_to_out(row) for row in rows]


async def get_agent_runs(
    db: AsyncSession,
    portfolio_id,
    limit: int = 20,
) -> list[AgentRun]:
    await heal_stale_agent_runs(db, portfolio_id=portfolio_id)
    stmt = (
        select(AgentRun)
        .where(AgentRun.portfolio_id == portfolio_id)
        .order_by(desc(AgentRun.started_at))
        .limit(limit)
    )
    return list((await db.scalars(stmt)).all())
