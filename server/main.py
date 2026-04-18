from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api import admin, agent, auth, dashboard, market, models as models_api, portfolios, trades
from core.config import settings
from core.database import get_db, init_models
from core.security import auth_middleware
from scheduler.jobs import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        await init_models()

    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(
    title="AlphaEngine Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(auth_middleware)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": db_status,
    }


app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(trades.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(models_api.router, prefix="/api/v1")
