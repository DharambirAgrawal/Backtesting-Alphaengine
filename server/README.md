# AlphaEngine Backend

FastAPI backend for AlphaEngine paper-trading platform.

## Quick Start

1. Create environment and install deps:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.3.0
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
- `AGENT_DECISION_MODE` (`rules`, `hybrid`, `gemini`)
- `STOOQ_API_KEY`
- `NEWS_API_KEY`
- `ALPHA_VANTAGE_KEY`
- `RENDER_EXTERNAL_URL`

## Market data and scheduling

- **Real data:** Quotes use real providers only (Stooq/Yahoo/Alpha Vantage). When markets are closed, daily feeds still return the **last completed session** close.
- **Holidays / weekends:** Scheduling skips non-trading days using market-day guards.
- **Agent schedule:** Fixed multi-run baseline and adaptive per-portfolio follow-up scheduling are both enabled by backend constants in `core/config.py`. Dashboard `next_run` reflects the earliest scheduled time for that portfolio.
- **Decision engine:** `AGENT_DECISION_MODE=hybrid` combines deterministic rules + model/news signals + Gemini interpretation, with hard risk rails before any trade executes.
