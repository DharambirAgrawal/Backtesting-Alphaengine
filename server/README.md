# AlphaEngine Backend

FastAPI backend for AlphaEngine paper-trading platform.

## Quick Start

1. Create environment and install deps:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and fill required values.

3. Initialize database and seed admin user:

```bash
python scripts/init_db.py
python scripts/seed_admin.py
```

4. Run the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The app serves health at `/health` and API routes under `/api/v1`.

## Required Environment Variables

- `DATABASE_URL`
- `JWT_SECRET`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## Optional (but recommended)

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_BUCKET`
- `GEMINI_API_KEY`
- `NEWS_API_KEY`
- `ALPHA_VANTAGE_KEY`
- `CORS_ORIGINS`
- `MARKET_TIMEZONE`
- `KEEP_ALIVE_URL`

## Market data and scheduling

- **Real data:** By default (`ALLOW_SYNTHETIC_MARKET_DATA=false`) all quotes use Stooq/Yahoo/Alpha Vantage only. After the US cash session closes (for example 6:32 PM Central), daily feeds still return the **last completed session’s** close — that is real data, not intraday streaming.
- **Holidays / weekends:** The latest bar is the previous **trading** day from the provider; there is no fake fill price unless you explicitly enable synthetic mode for offline demos.
- **Agent schedule:** Automatic runs use **one** cron (`AGENT_CRON_*`, weekdays by default at 9:35 `MARKET_TIMEZONE`). Set `AGENT_CRON_ENABLED=false` for manual-only runs (`POST /api/v1/agent/{portfolio_id}/run`). The trading loop in `agent/runner.py` is currently **rule-based**; wiring an LLM to choose the *next* run time would be a separate feature.
