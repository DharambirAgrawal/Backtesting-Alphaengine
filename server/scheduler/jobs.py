from __future__ import annotations

import asyncio
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pandas.tseries.holiday import USFederalHolidayCalendar
from sqlalchemy import select

from agent.runner import run_agent
from core.config import settings
from core.database import SessionLocal
from core.models import Portfolio, PortfolioTicker
from ml.trainer import train_many_tickers

scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.MARKET_TIMEZONE))
_dynamic_jobs: dict[str, datetime] = {}


def _to_market_tz(dt: datetime) -> datetime:
    tz = ZoneInfo(settings.MARKET_TIMEZONE)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(tz)
    return dt.astimezone(tz)


@lru_cache(maxsize=1)
def _holiday_set_for_year(year: int) -> set[str]:
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=f"{year}-01-01", end=f"{year}-12-31")
    return {item.date().isoformat() for item in holidays}


def _is_trading_day(local_dt: datetime) -> bool:
    if local_dt.weekday() >= 5:
        return False
    return local_dt.date().isoformat() not in _holiday_set_for_year(local_dt.year)


def _next_trading_day_open(local_dt: datetime) -> datetime:
    """Advance until we land on a trading day at 09:35.
    We set hour=12 before adding a day so timedelta always crosses midnight
    cleanly; the next iteration immediately overwrites hour back to 09:35.
    """
    cursor = local_dt
    while True:
        cursor = cursor.replace(hour=9, minute=35, second=0, microsecond=0)
        if _is_trading_day(cursor):
            return cursor
        # Move the clock to midday before advancing — avoids DST edge cases
        cursor = cursor.replace(hour=12, minute=0, second=0, microsecond=0)
        cursor = cursor + timedelta(days=1)


def compute_next_market_run(
    *,
    preferred_minutes: int,
    now_utc: datetime | None = None,
) -> datetime:
    now_utc = now_utc or datetime.now(timezone.utc)
    local_now = _to_market_tz(now_utc)
    open_time = local_now.replace(hour=9, minute=35, second=0, microsecond=0)
    close_time = local_now.replace(hour=15, minute=50, second=0, microsecond=0)

    if not _is_trading_day(local_now) or local_now >= close_time:
        nxt = _next_trading_day_open(local_now + timedelta(days=1))
        return nxt.astimezone(timezone.utc)

    base = max(local_now, open_time)
    candidate = base + timedelta(minutes=max(20, preferred_minutes))
    if candidate > close_time:
        nxt = _next_trading_day_open(local_now + timedelta(days=1))
        return nxt.astimezone(timezone.utc)
    return candidate.astimezone(timezone.utc)


async def run_all_portfolios(session: str) -> None:
    async with SessionLocal() as db:
        stmt = select(Portfolio.id).where(Portfolio.is_active.is_(True))
        portfolio_ids = [str(item) for item in (await db.scalars(stmt)).all()]

    tasks = [
        run_agent(portfolio_id=pid, session=session, run_type="scheduled") for pid in portfolio_ids
    ]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def run_single_portfolio_scheduled(portfolio_id: str, session: str = "adaptive") -> None:
    await run_agent(portfolio_id=portfolio_id, session=session, run_type="scheduled")


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
    return get_next_run_time_for_portfolio()


def get_next_run_time_for_portfolio(portfolio_id: str | None = None) -> datetime | None:
    now = datetime.now(timezone.utc)
    next_runs: list[datetime] = []
    for job in scheduler.get_jobs():
        if not job.id.startswith("agent-scheduled-"):
            continue
        if job.next_run_time and job.next_run_time >= now:
            next_runs.append(job.next_run_time)
    if portfolio_id:
        dynamic = _dynamic_jobs.get(portfolio_id)
        if dynamic and dynamic >= now:
            next_runs.append(dynamic)
    return min(next_runs) if next_runs else None


def schedule_portfolio_run(
    *,
    portfolio_id: str,
    run_at_utc: datetime,
    session: str = "adaptive",
) -> None:
    if run_at_utc.tzinfo is None:
        run_at_utc = run_at_utc.replace(tzinfo=timezone.utc)
    job_id = f"agent-dynamic-{portfolio_id}"
    scheduler.add_job(
        run_single_portfolio_scheduled,
        trigger=DateTrigger(run_date=run_at_utc),
        kwargs={"portfolio_id": portfolio_id, "session": session},
        id=job_id,
        replace_existing=True,
    )
    _dynamic_jobs[portfolio_id] = run_at_utc


def start_scheduler() -> None:
    if scheduler.running:
        return

    if settings.AGENT_CRON_ENABLED:
        for hour in settings.agent_cron_hours:
            scheduler.add_job(
                run_all_portfolios,
                trigger=CronTrigger(
                    day_of_week=settings.AGENT_CRON_DAY_OF_WEEK,
                    hour=hour,
                    minute=settings.AGENT_CRON_MINUTE,
                    timezone=ZoneInfo(settings.MARKET_TIMEZONE),
                ),
                kwargs={"session": "scheduled"},
                id=f"agent-scheduled-{hour:02d}",
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
