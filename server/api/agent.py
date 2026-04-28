from __future__ import annotations

import asyncio
import math
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.runner import run_agent
from api.deps import get_current_user, get_portfolio_or_404
from api.utils import as_float, heal_stale_agent_runs, transaction_to_out
from core.database import get_db
from core.models import AgentRun, Portfolio, Transaction, User
from core.schemas import AgentRunDetailOut, AgentRunOut, AgentRunTickerDetailOut, MessageResponse

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


def _extract_evaluations_from_summary(summary: str | None) -> list[dict[str, str]]:
    if not summary:
        return []

    evaluations: list[dict[str, str]] = []
    action_pattern = re.compile(
        r"^(?P<ticker>[A-Z][A-Z0-9.\-]*)\:.*Action=(?P<action>BUY|SELL|HOLD)\.",
        re.IGNORECASE,
    )
    skipped_pattern = re.compile(
        r"^(?P<ticker>[A-Z][A-Z0-9.\-]*)\:\s+skipped due to tool error",
        re.IGNORECASE,
    )

    for raw_line in summary.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        action_match = action_pattern.match(line)
        if action_match:
            evaluations.append(
                {
                    "ticker": action_match.group("ticker").upper(),
                    "action": action_match.group("action").upper(),
                    "summary_line": line,
                }
            )
            continue

        skipped_match = skipped_pattern.match(line)
        if skipped_match:
            evaluations.append(
                {
                    "ticker": skipped_match.group("ticker").upper(),
                    "action": "HOLD",
                    "summary_line": line,
                }
            )

    return evaluations


def _coerce_tools_called(value) -> dict:
    return value if isinstance(value, dict) else {}


async def _build_agent_run_detail(
    db: AsyncSession,
    portfolio_id,
    run: AgentRun,
) -> AgentRunDetailOut:
    tx_stmt = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .where(Transaction.idempotency_key.ilike(f"{run.id}:%"))
        .order_by(Transaction.executed_at.asc())
    )
    run_transactions = list((await db.scalars(tx_stmt)).all())

    details: list[AgentRunTickerDetailOut] = []
    transaction_map: dict[tuple[str, str], Transaction] = {
        (tx.ticker.upper(), tx.action.upper()): tx for tx in run_transactions
    }
    seen: set[tuple[str, str]] = set()

    if run.per_ticker_decisions:
        for item in run.per_ticker_decisions:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker") or "").upper().strip()
            action = str(item.get("action") or "HOLD").upper().strip()
            if not ticker:
                continue
            key = (ticker, action)
            tx = transaction_map.get(key)
            seen.add(key)
            details.append(
                AgentRunTickerDetailOut(
                    ticker=ticker,
                    action=action,
                    llm_reasoning=str(item.get("rationale") or item.get("llm_reasoning") or ""),
                    tools_called=_coerce_tools_called(item.get("tools_called")),
                    transaction=transaction_to_out(tx) if tx else None,
                    summary_line=None,
                )
            )
    else:
        summary_items = _extract_evaluations_from_summary(run.summary)
        for item in summary_items:
            key = (item["ticker"], item["action"])
            tx = transaction_map.get(key)
            seen.add(key)
            details.append(
                AgentRunTickerDetailOut(
                    ticker=item["ticker"],
                    action=item["action"],
                    llm_reasoning=(tx.llm_reasoning if tx and tx.llm_reasoning else item["summary_line"]),
                    tools_called=(tx.tools_called if tx and tx.tools_called else {}),
                    transaction=transaction_to_out(tx) if tx else None,
                    summary_line=item["summary_line"],
                )
            )

    for tx in run_transactions:
        key = (tx.ticker.upper(), tx.action.upper())
        if key in seen:
            continue
        details.append(
            AgentRunTickerDetailOut(
                ticker=tx.ticker.upper(),
                action=tx.action.upper(),
                llm_reasoning=tx.llm_reasoning or "",
                tools_called=tx.tools_called or {},
                transaction=transaction_to_out(tx),
                summary_line=None,
            )
        )

    run_out = _to_agent_run_out(run)
    return AgentRunDetailOut(
        **run_out.model_dump(),
        evaluations=details,
        held_all_positions=bool(details) and run.trades_made == 0 and all(
            item.action.upper() == "HOLD" for item in details
        ),
    )


@router.post("/agent/{portfolio_id}/run", response_model=AgentRunOut)
async def trigger_agent_run(
    portfolio_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)

    # Defensive cleanup: avoid stale "running" rows blocking manual triggers.
    await heal_stale_agent_runs(db, portfolio_id=portfolio.id)

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
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)

    # Defensive cleanup for UI correctness.
    await heal_stale_agent_runs(db, portfolio_id=portfolio.id)

    stmt = (
        select(AgentRun)
        .where(AgentRun.portfolio_id == portfolio.id)
        .order_by(desc(AgentRun.started_at))
        .limit(100)
    )
    runs = (await db.scalars(stmt)).all()
    return [_to_agent_run_out(run) for run in runs]


@router.get("/agent/{portfolio_id}/runs/{run_id}", response_model=AgentRunDetailOut)
async def get_agent_run(
    portfolio_id: str,
    run_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)

    stmt = select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.portfolio_id == portfolio.id,
    )
    run = await db.scalar(stmt)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return await _build_agent_run_detail(db, portfolio.id, run)


@router.post("/agent/{portfolio_id}/pause", response_model=MessageResponse)
async def pause_agent(
    portfolio_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)
    portfolio.is_active = False
    await db.commit()
    return MessageResponse(message="Agent paused")


@router.post("/agent/{portfolio_id}/resume", response_model=MessageResponse)
async def resume_agent(
    portfolio_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)
    portfolio.is_active = True
    await db.commit()
    return MessageResponse(message="Agent resumed")
