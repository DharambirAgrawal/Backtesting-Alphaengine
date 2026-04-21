from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_admin_user
from core.database import get_db
from core.models import User
from core.schemas import MessageResponse, UserCreateRequest, UserOut, UserUpdateRequest
from core.security import hash_password

router = APIRouter(tags=["admin"])


@router.get("/admin/users", response_model=list[UserOut])
async def list_users(
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.asc())
    rows = (await db.scalars(stmt)).all()
    users: list[UserOut] = []
    for row in rows:
        try:
            users.append(
                UserOut(
                    id=row.id,
                    email=row.email,
                    role=row.role,
                    is_active=row.is_active,
                    created_at=row.created_at,
                )
            )
        except ValidationError:
            # Skip malformed legacy rows so admin endpoints remain available.
            continue

    return users


@router.post("/admin/users", response_model=MessageResponse)
async def create_user(
    payload: UserCreateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    await db.commit()

    return MessageResponse(message=f"User {user.email} created")


@router.patch("/admin/users/{user_id}", response_model=MessageResponse)
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    _: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.email:
        conflict = await db.scalar(
            select(User).where(User.email == payload.email.lower(), User.id != user.id)
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = payload.email.lower()

    if payload.password:
        user.password_hash = hash_password(payload.password)

    if not payload.email and not payload.password:
        raise HTTPException(status_code=400, detail="No changes provided")

    await db.commit()
    return MessageResponse(message="User updated")


@router.delete("/admin/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if str(current_admin.id) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return MessageResponse(message="User deleted")
