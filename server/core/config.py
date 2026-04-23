from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Auth
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None
    JWT_SECRET: str | None = None
    JWT_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str | None = None

    # Supabase
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None
    SUPABASE_BUCKET: str = "alphaengine-models"

    # LLM
    GEMINI_API_KEY: str | None = None
    AGENT_DECISION_MODE: str = "hybrid"  # accepted: rules | hybrid | gemini

    # Market data
    ALPHA_VANTAGE_KEY: str | None = None
    NEWS_API_KEY: str | None = None
    # Ticker search providers (Finnhub is the primary; Alpha Vantage is fallback)
    FINNHUB_API_KEY: str | None = None
    # OHLCV data providers (separate from search — Stooq works for historical data)
    STOOQ_API_KEY: str | None = None
    STOOQ_FIRST: bool = True
    ALLOW_SYNTHETIC_MARKET_DATA: bool = False
    ALLOW_SYNTHETIC_NEWS: bool = False

    # Scheduler
    AGENT_CRON_ENABLED: bool = True
    AGENT_CRON_DAY_OF_WEEK: str = "mon-fri"
    AGENT_CRON_HOUR: int = 9
    AGENT_CRON_MINUTE: int = 35
    AGENT_CRON_HOURS: str | None = "9,12,15"

    # App
    ENVIRONMENT: str = "production"
    MARKET_TIMEZONE: str = "America/New_York"
    CORS_ORIGINS: str = "http://localhost:3000,https://alphaenginestock.vercel.app"
    KEEP_ALIVE_URL: str = "http://127.0.0.1:8000/health"
    RENDER_EXTERNAL_URL: str | None = None
    AUTO_CREATE_TABLES: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url_async(self) -> str:
        """Normalize common Render/Postgres URLs for SQLAlchemy async engine."""
        if not self.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is required in environment.")
        url = self.DATABASE_URL.strip()
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def keep_alive_url(self) -> str:
        if self.RENDER_EXTERNAL_URL:
            base = self.RENDER_EXTERNAL_URL.rstrip("/")
            return f"{base}/health"
        return self.KEEP_ALIVE_URL

    @property
    def jwt_secret(self) -> str:
        if not self.JWT_SECRET or len(self.JWT_SECRET.strip()) < 32:
            raise RuntimeError("JWT_SECRET must be set and at least 32 characters.")
        return self.JWT_SECRET.strip()

    @property
    def agent_cron_hours(self) -> list[int]:
        if not self.AGENT_CRON_HOURS:
            return [self.AGENT_CRON_HOUR]
        values: list[int] = []
        for raw in self.AGENT_CRON_HOURS.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                hour = int(raw)
            except ValueError:
                continue
            if 0 <= hour <= 23:
                values.append(hour)
        return sorted(set(values)) or [self.AGENT_CRON_HOUR]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
