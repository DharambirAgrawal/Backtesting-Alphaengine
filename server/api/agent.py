from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.runner import run_agent
from api.deps import get_current_user, get_portfolio_or_404
from api.utils import as_float
from core.database import get_db
from core.models import AgentRun, Portfolio, User
from core.schemas import AgentRunOut, MessageResponse

router = APIRouter(tags=["agent"])


def _to_agent_run_out(run: AgentRun) -> AgentRunOut:
    return AgentRunOut(
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


@router.post("/agent/{portfolio_id}/run", response_model=AgentRunOut)
async def trigger_agent_run(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)

    running_stmt = select(AgentRun.id).where(
        AgentRun.portfolio_id == portfolio.id,
        AgentRun.status == "running",
    )
    running_run_id = await db.scalar(running_stmt)
    if running_run_id:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    completed_stmt = (
        select(AgentRun.completed_at)
        .where(
            AgentRun.portfolio_id == portfolio.id,
            AgentRun.completed_at.is_not(None),
        )
        .order_by(desc(AgentRun.completed_at))
        .limit(1)
    )
    last_completed_at = await db.scalar(completed_stmt)
    if last_completed_at:
        now = datetime.now(timezone.utc)
        elapsed_minutes = (now - last_completed_at).total_seconds() / 60.0
        if elapsed_minutes < 10:
            wait_minutes = max(1, math.ceil(10 - elapsed_minutes))
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait_minutes} minutes before triggering another run",
            )

    run = AgentRun(
        portfolio_id=portfolio.id,
        run_type="manual",
        session="manual",
        summary="",
        trades_made=0,
        total_pl=0,
        status="running",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    asyncio.create_task(
        run_agent(
            portfolio_id=str(portfolio.id),
            session="manual",
            run_type="manual",
            run_id=str(run.id),
        )
    )

    return _to_agent_run_out(run)


@router.get("/agent/{portfolio_id}/runs", response_model=list[AgentRunOut])
async def get_agent_runs(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)

    stmt = (
        select(AgentRun)
        .where(AgentRun.portfolio_id == portfolio.id)
        .order_by(desc(AgentRun.started_at))
        .limit(100)
    )
    runs = (await db.scalars(stmt)).all()
    return [_to_agent_run_out(run) for run in runs]


@router.get("/agent/{portfolio_id}/runs/{run_id}", response_model=AgentRunOut)
async def get_agent_run(
    portfolio_id: str,
    run_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)

    stmt = select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.portfolio_id == portfolio.id,
    )
    run = await db.scalar(stmt)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return _to_agent_run_out(run)


@router.post("/agent/{portfolio_id}/pause", response_model=MessageResponse)
async def pause_agent(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    portfolio.is_active = False
    await db.commit()
    return MessageResponse(message="Agent paused")


@router.post("/agent/{portfolio_id}/resume", response_model=MessageResponse)
async def resume_agent(
    portfolio_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, db)
    portfolio.is_active = True
    await db.commit()
    return MessageResponse(message="Agent resumed")
