from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_portfolio_or_404
from api.utils import transaction_to_out
from core.database import get_db
from core.models import Transaction, User
from core.schemas import PaginatedTransactionsOut, TransactionOut

router = APIRouter(tags=["trades"])


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


@router.get(
    "/portfolios/{portfolio_id}/transactions",
    response_model=PaginatedTransactionsOut,
)
async def list_transactions(
    portfolio_id: str,
    request: Request,
    ticker: str | None = None,
    action: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    search: str | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)

    stmt = select(Transaction).where(Transaction.portfolio_id == portfolio.id)

    if ticker:
        stmt = stmt.where(Transaction.ticker == ticker.upper().strip())

    if action:
        stmt = stmt.where(Transaction.action == action.upper().strip())

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Transaction.ticker.ilike(term),
                Transaction.llm_reasoning.ilike(term),
            )
        )

    parsed_from = _parse_datetime(from_date)
    if parsed_from:
        stmt = stmt.where(Transaction.executed_at >= parsed_from)

    parsed_to = _parse_datetime(to_date)
    if parsed_to:
        stmt = stmt.where(Transaction.executed_at <= parsed_to)

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = int((await db.scalar(total_stmt)) or 0)

    page_stmt = stmt.order_by(desc(Transaction.executed_at)).limit(limit).offset(offset)
    rows = (await db.scalars(page_stmt)).all()

    return PaginatedTransactionsOut(
        transactions=[transaction_to_out(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/portfolios/{portfolio_id}/transactions/{tx_id}",
    response_model=TransactionOut,
)
async def get_transaction(
    portfolio_id: str,
    tx_id: str,
    request: Request,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await get_portfolio_or_404(portfolio_id, request, db)

    stmt = select(Transaction).where(
        Transaction.id == tx_id,
        Transaction.portfolio_id == portfolio.id,
    )
    tx = await db.scalar(stmt)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction_to_out(tx)
