from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url_async,
    echo=not settings.is_production,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    # Import models so metadata is populated before create_all.
    from core import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
