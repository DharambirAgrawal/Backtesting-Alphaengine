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
    JWT_SECRET: str = "change-me-with-a-long-random-secret-at-least-32-chars"
    JWT_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/alphaengine"
    )

    # Supabase
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None
    SUPABASE_BUCKET: str = "alphaengine-models"

    # AI
    GEMINI_API_KEY: str | None = None

    # Market data (real providers only when synthetic is off — see IDEA.md / README)
    ALPHA_VANTAGE_KEY: str | None = None
    NEWS_API_KEY: str | None = None
    STOOQ_API_KEY: str | None = None
    # Prefer Stooq CSV before Yahoo when Yahoo blocks your IP (Codespaces / many hosts).
    STOOQ_FIRST: bool = True
    # When False (default), never invent OHLCV or hash-based prices — APIs must succeed.
    ALLOW_SYNTHETIC_MARKET_DATA: bool = False
    # When False (default), do not inject fake news headlines if NewsAPI fails or is missing.
    ALLOW_SYNTHETIC_NEWS: bool = False
    # When False (default), ticker search returns empty if Yahoo search fails (no static demo list).
    ALLOW_SEARCH_FALLBACK_TICKERS: bool = False

    # Agent scheduler: one cron per trading week (replace legacy 3× daily demo slots).
    # When disabled, only manual POST /agent/{id}/run triggers runs.
    AGENT_CRON_ENABLED: bool = True
    AGENT_CRON_DAY_OF_WEEK: str = "mon-fri"
    AGENT_CRON_HOUR: int = 9
    AGENT_CRON_MINUTE: int = 35

    # App
    APP_SECRET: str = "dev-secret"
    ENVIRONMENT: str = "development"
    MARKET_TIMEZONE: str = "America/New_York"
    CORS_ORIGINS: str = "http://localhost:3000"
    KEEP_ALIVE_URL: str = "http://127.0.0.1:8000/health"
    AUTO_CREATE_TABLES: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url_async(self) -> str:
        """Normalize common Render/Postgres URLs for SQLAlchemy async engine."""
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
