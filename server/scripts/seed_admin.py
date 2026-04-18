import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
load_dotenv(ROOT / ".env")

from core.database import get_session
from core.models import User
from core.security import hash_password


async def seed() -> None:
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        print("ERROR: Set ADMIN_EMAIL and ADMIN_PASSWORD in your environment first.")
        return

    async with get_session() as db:
        existing = await db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            existing.role = "admin"
            existing.is_active = True
            existing.password_hash = hash_password(password)
            await db.commit()
            print(f"Admin user updated: {email.lower()}")
            return

        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"Admin user seeded: {email.lower()}")


if __name__ == "__main__":
    asyncio.run(seed())
