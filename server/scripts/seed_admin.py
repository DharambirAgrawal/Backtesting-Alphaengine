import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
load_dotenv(ROOT / ".env")

from core.database import get_session
from core.models import User
from core.security import hash_password

email_adapter = TypeAdapter(EmailStr)


async def seed() -> None:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: Set ADMIN_EMAIL and ADMIN_PASSWORD in your environment first.")
        return

    try:
        normalized_email = str(email_adapter.validate_python(email)).lower()
    except ValidationError:
        print("ERROR: ADMIN_EMAIL is not a valid email address.")
        return

    async with get_session() as db:
        existing = await db.scalar(select(User).where(User.email == normalized_email))
        if existing:
            existing.role = "admin"
            existing.is_active = True
            existing.password_hash = hash_password(password)
            await db.commit()
            print(f"Admin user updated: {normalized_email}")
            return

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"Admin user seeded: {normalized_email}")


if __name__ == "__main__":
    asyncio.run(seed())
