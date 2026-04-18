from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

from core.config import settings

OPEN_PATHS = {
    "/health",
    "/api/v1/auth/login",
}
OPEN_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(payload: dict[str, Any]) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_EXPIRE_DAYS
    )
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if path in OPEN_PATHS or any(path.startswith(prefix) for prefix in OPEN_PREFIXES):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()

    if not token:
        return JSONResponse({"error": "Unauthorized"}, status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = decode_access_token(token)
        request.state.user_id = payload.get("sub")
        request.state.role = payload.get("role")
        request.state.email = payload.get("email")
        if not request.state.user_id:
            raise ValueError("Missing sub claim")
    except (JWTError, ValueError):
        return JSONResponse({"error": "Unauthorized"}, status_code=status.HTTP_401_UNAUTHORIZED)

    return await call_next(request)


def require_admin(request: Request) -> None:
    if getattr(request.state, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
