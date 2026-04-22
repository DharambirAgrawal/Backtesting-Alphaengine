from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from agent.runner import run_agent
from core.config import settings
from core.database import SessionLocal
from core.models import Portfolio, PortfolioTicker
from ml.trainer import train_many_tickers

scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.MARKET_TIMEZONE))


async def run_all_portfolios(session: str) -> None:
    async with SessionLocal() as db:
        stmt = select(Portfolio.id).where(Portfolio.is_active.is_(True))
        portfolio_ids = [str(item) for item in (await db.scalars(stmt)).all()]

    tasks = [
        run_agent(portfolio_id=pid, session=session, run_type="scheduled") for pid in portfolio_ids
    ]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def retrain_all_models_job() -> None:
    async with SessionLocal() as db:
        stmt = select(PortfolioTicker.ticker).distinct()
        tickers = [str(item).upper() for item in (await db.scalars(stmt)).all()]
        if tickers:
            await train_many_tickers(db, tickers)


async def keep_alive_ping() -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(settings.keep_alive_url)
    except Exception:
        return


def get_next_run_time() -> datetime | None:
    now = datetime.now(timezone.utc)
    job = scheduler.get_job("agent-scheduled")
    if not job or not job.next_run_time:
        return None
    if job.next_run_time >= now:
        return job.next_run_time
    return None


def start_scheduler() -> None:
    if scheduler.running:
        return

    if settings.AGENT_CRON_ENABLED:
        scheduler.add_job(
            run_all_portfolios,
            trigger=CronTrigger(
                day_of_week=settings.AGENT_CRON_DAY_OF_WEEK,
                hour=settings.AGENT_CRON_HOUR,
                minute=settings.AGENT_CRON_MINUTE,
                timezone=ZoneInfo(settings.MARKET_TIMEZONE),
            ),
            kwargs={"session": "scheduled"},
            id="agent-scheduled",
            replace_existing=True,
        )

    scheduler.add_job(
        retrain_all_models_job,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="UTC"),
        id="retrain-weekly",
        replace_existing=True,
    )

    scheduler.add_job(
        keep_alive_ping,
        trigger=IntervalTrigger(minutes=10),
        id="keep-alive",
        replace_existing=True,
    )

    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
