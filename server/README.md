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
