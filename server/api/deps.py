from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Portfolio, User
from core.security import require_admin


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    return user


async def get_admin_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    require_admin(request)
    return await get_current_user(request, db)


async def get_portfolio_or_404(
    portfolio_id: str,
    request: Request,
    db: AsyncSession,
) -> Portfolio:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    role = getattr(request.state, "role", None)
    user_id = getattr(request.state, "user_id", None)
    if role != "admin" and str(portfolio.owner_user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    return portfolio
