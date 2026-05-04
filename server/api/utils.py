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


# Simple in-memory price cache with TTL (5 minutes)
_price_cache: dict[str, tuple[float, float]] = {}  # {ticker: (price, timestamp_utc_seconds)}
_PRICE_CACHE_TTL = 300.0  # 5 minutes
_PRICE_CACHE_STALE_TTL = 3600.0  # 1 hour


def _get_cached_price(ticker: str, *, allow_stale: bool = False) -> float | None:
    """Get cached price if exists and not expired (or allow stale within max age)."""
    symbol = ticker.strip().upper()
    entry = _price_cache.get(symbol)
    if not entry:
        return None
    price, ts = entry
    now = datetime.now(timezone.utc).timestamp()
    age = now - ts
    if age <= _PRICE_CACHE_TTL:
        return price
    if allow_stale and age <= _PRICE_CACHE_STALE_TTL:
        return price
    if age > _PRICE_CACHE_STALE_TTL:
        _price_cache.pop(symbol, None)
    return None


def _set_cached_price(ticker: str, price: float) -> None:
    """Cache a price for 5 minutes."""
    symbol = ticker.strip().upper()
    _price_cache[symbol] = (price, datetime.now(timezone.utc).timestamp())


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
    stale_after_minutes: int = 180,
) -> int:
    """Mark long-running agent runs as failed so they don't block new runs.

    This primarily defends against crashes/lock contention bugs that leave rows in
    a perpetual "running" state.
    """

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=stale_after_minutes)

    # Fetch all currently-running rows (for a portfolio if provided).
    running_stmt = (
        select(AgentRun)
        .where(AgentRun.status == "running")
        .where(AgentRun.completed_at.is_(None))
        .order_by(AgentRun.started_at.asc())
    )
    if portfolio_id is not None:
        running_stmt = running_stmt.where(AgentRun.portfolio_id == portfolio_id)

    running_runs = list((await db.scalars(running_stmt)).all())
    if not running_runs:
        return 0

    # If we know a later run completed, any older "running" row is impossible
    # (per-portfolio advisory lock enforces single-run execution).
    latest_completed_at: datetime | None = None
    if portfolio_id is not None:
        completed_stmt = (
            select(AgentRun.completed_at)
            .where(AgentRun.portfolio_id == portfolio_id)
            .where(AgentRun.completed_at.is_not(None))
            .order_by(AgentRun.completed_at.desc())
            .limit(1)
        )
        latest_completed_at = await db.scalar(completed_stmt)

    stale_runs: list[AgentRun] = []
    for run in running_runs:
        impossible = bool(latest_completed_at and latest_completed_at > run.started_at)
        too_old = run.started_at < cutoff
        if impossible or too_old:
            stale_runs.append(run)

    if not stale_runs:
        return 0

    for run in stale_runs:
        run.status = "failed"
        minutes_running = max(0, int((now - run.started_at).total_seconds() // 60))
        note = (
            "Skipped: run was marked stale (stuck in running state). "
            f"Elapsed≈{minutes_running}m; threshold={stale_after_minutes}m."
        )
        existing = (run.summary or "").strip()
        run.summary = existing + ("\n\n" if existing else "") + note
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


async def _price_for_holding(ticker: str, avg_buy: float) -> tuple[float, str, str | None]:
    """Fetch current price with caching and timeout.

    Returns (price, source, error). Source indicates whether live, cache, stale_cache,
    or avg_buy was used. Error is set when live fetch failed.
    """
    # Check cache first
    cached = _get_cached_price(ticker)
    if cached is not None:
        return cached, "cache", None

    stale_cached = _get_cached_price(ticker, allow_stale=True)

    try:
        # Fetch price with a bounded timeout to avoid slow requests
        price = await asyncio.wait_for(get_current_price(ticker), timeout=8.0)
        _set_cached_price(ticker, price)
        return price, "live", None
    except asyncio.TimeoutError:
        error = "market data request timed out"
        if stale_cached is not None:
            return stale_cached, "stale_cache", error
        return avg_buy, "avg_buy", error
    except MarketDataUnavailableError as exc:
        error = str(exc)
        if stale_cached is not None:
            return stale_cached, "stale_cache", error
        return avg_buy, "avg_buy", error
    except Exception as exc:
        error = f"market data error: {exc}"
        if stale_cached is not None:
            return stale_cached, "stale_cache", error
        return avg_buy, "avg_buy", error


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

    sem = asyncio.Semaphore(3)
    
    async def _fetch_with_sem(row):
        async with sem:
            return await _price_for_holding(row.ticker, as_float(row.avg_buy_price))
            
    prices = await asyncio.gather(*[_fetch_with_sem(row) for row in eligible])

    output: list[HoldingOut] = []
    holdings_value = 0.0

    for row, price_payload in zip(eligible, prices, strict=True):
        current_price, price_source, price_error = price_payload
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
                price_source=price_source,
                price_error=price_error,
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
) -> PerformanceStatsOut:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("Portfolio not found")


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
        total_return_pct=0.0,
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
