from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_portfolio_or_404
from api.utils import (
    as_float,
    build_holdings_view,
    build_performance_stats,
    get_agent_runs,
    get_portfolio_tickers,
    get_recent_transactions,
    snapshot_portfolio,
    _portfolio_out_from_values,
)
from core.database import get_db
from core.models import PortfolioSnapshot, User
from core.schemas import AgentRunOut, ChartDataOut, DashboardOut, PerformanceStatsOut
from scheduler.jobs import get_next_run_time_for_portfolio

router = APIRouter(tags=["dashboard"])


def _period_to_days(period: str) -> int | None:
    normalized = period.upper().strip()
    mapping = {
        "1W": 7,
        "1M": 30,
        "3M": 90,
        "ALL": None,
    }
    return mapping.get(normalized, 30)


@router.get("/dashboard/{portfolio_id}", response_model=DashboardOut)
async def get_dashboard(
    portfolio_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)

    # Fetch all data in parallel for better performance
    holdings_task = asyncio.create_task(build_holdings_view(db, portfolio.id))
    tickers_task = asyncio.create_task(get_portfolio_tickers(db, portfolio.id))
    performance_task = None  # Will fetch after holdings
    recent_transactions_task = asyncio.create_task(get_recent_transactions(db, portfolio.id, limit=5))
    agent_runs_task = asyncio.create_task(get_agent_runs(db, portfolio.id, limit=10))

    # Wait for initial tasks
    holdings, holdings_value = await holdings_task
    tickers = await tickers_task
    portfolio_out = _portfolio_out_from_values(portfolio, tickers, holdings_value)
    
    # Now fetch performance with the portfolio_out we have
    performance_task = asyncio.create_task(
        build_performance_stats(db, portfolio.id, portfolio_out=portfolio_out)
    )
    
    recent_transactions = await recent_transactions_task
    runs = await agent_runs_task
    performance = await performance_task

    next_run_dt = (
        get_next_run_time_for_portfolio(str(portfolio.id)) if portfolio.is_active else None
    )
    next_run = next_run_dt.isoformat() if next_run_dt else None

    return DashboardOut(
        portfolio=portfolio_out,
        performance=performance,
        holdings=holdings,
        recent_transactions=recent_transactions,
        agent_runs=[
            AgentRunOut(
                id=run.id,
                portfolio_id=run.portfolio_id,
                run_type=run.run_type,
                session=run.session,
                summary=run.summary,
                trades_made=run.trades_made,
                total_pl=as_float(run.total_pl),
                started_at=run.started_at,
                completed_at=run.completed_at,
                status=run.status,
            )
            for run in runs
        ],
        next_run=next_run,
    )


@router.get("/dashboard/{portfolio_id}/chart", response_model=ChartDataOut)
async def get_dashboard_chart(
    portfolio_id: str,
    request: Request,
    period: str = Query(default="1M"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)
    days = _period_to_days(period)

    stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio.id)
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(PortfolioSnapshot.snapshot_at >= cutoff)

    stmt = stmt.order_by(PortfolioSnapshot.snapshot_at.asc())
    snapshots = (await db.scalars(stmt)).all()

    if not snapshots:
        await snapshot_portfolio(db, portfolio.id)
        snapshots = (await db.scalars(stmt)).all()

    labels = [item.snapshot_at.date().isoformat() for item in snapshots]
    total_values = [round(as_float(item.total_value), 2) for item in snapshots]
    cash_values = [round(as_float(item.cash_value), 2) for item in snapshots]
    holdings_values = [round(as_float(item.holdings_value), 2) for item in snapshots]

    return ChartDataOut(
        labels=labels,
        total_value=total_values,
        cash=cash_values,
        holdings=holdings_values,
    )


@router.get("/dashboard/{portfolio_id}/performance", response_model=PerformanceStatsOut)
async def get_dashboard_performance(
    portfolio_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _portfolio = await get_portfolio_or_404(portfolio_id, request, db)
    return await build_performance_stats(db, portfolio_id)
