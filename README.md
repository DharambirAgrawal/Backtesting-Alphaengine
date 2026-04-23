# AlphaEngine

**AlphaEngine** is a paper-trading platform: you run virtual portfolios with real market data, optional ML models (LSTM + XGBoost), and an automated agent that can buy and sell **without real money**. It is built for learning quant workflows, testing ideas, and seeing full decision traces—not for live brokerage execution.

Live demo (when deployed): [alphaenginestock.vercel.app](https://alphaenginestock.vercel.app) (login required).

---

## What it does

1. **Portfolios** — Create one or more portfolios with a starting cash balance and a list of **valid stock tickers** (e.g. `AAPL`, `GOOGL`, not company names like `AMAZON`).
2. **Market data** — Prices and history come from real providers (Stooq with API key, Yahoo when available, Alpha Vantage as fallback). After the US session closes, you still get the **last completed session’s** daily prices—there is no need for the exchange to be open for the app to value positions.
3. **Models** — For each ticker you can train **two** model types stored in the **global model registry** (shared across portfolios that use the same ticker):
   - **LSTM** — sequence model on technical features; used in price-style signals.
   - **XGBoost** — classifier for short-horizon **up / down** direction on held-out data.
4. **Agent** — On a schedule (or when you click **Run Now**), the agent evaluates each portfolio ticker and may place **BUY / SELL / HOLD** paper trades. Trades and reasoning are stored for the dashboard.
5. **Dashboard** — Portfolio value, cash vs holdings, holdings table, recent trades, charts from snapshots, and **next scheduled agent run** (when the backend scheduler is enabled).

---

## Global Model Registry (what you see in the UI)

The **Global Model Registry** page answers one question: *for every ticker any portfolio depends on, do we have trained LSTM and XGBoost rows ready?*

- **Tracked tickers** — Distinct symbols listed on portfolios.
- **Coverage** — For each ticker, whether both `lstm` and `xgboost` exist in `ModelRegistry`.
- **Retrain all** — Retrains all tracked tickers (can take a while; depends on host CPU and data providers).
- **Per-ticker retrain** — Retrains that symbol only.

Models are **global per ticker**, not per portfolio: if two portfolios both hold `NVDA`, they share the same registry entry for `NVDA`.

### Why accuracy often looks ~50–55%

The XGBoost metric is **out-of-sample accuracy** on **next-day up vs down** from daily bars. That task is **hard**; many published baselines sit barely above 50%. Seeing **~50–54%** is therefore **not automatically “broken”**—it often means the model is near noise for that split. Improving it usually means richer features, different horizons, regime filters, or more careful validation—not a single magic number.

---

## How to use it (quick path)

### 1. Backend (FastAPI)

See `server/README.md` for install, env vars, DB seed, and run commands.

Important env vars (see `server/.env.example`):

- **Auth / DB** — `JWT_SECRET`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- **Market** — `STOOQ_API_KEY`, optional `ALPHA_VANTAGE_KEY`, `STOOQ_FIRST`
- **Model files** — `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET`
- **Render wake-ups** — `RENDER_EXTERNAL_URL` so scheduled keep-alive hits your public `/health`
- **Agent schedule** — `AGENT_CRON_ENABLED`, `AGENT_CRON_DAY_OF_WEEK`, `AGENT_CRON_HOUR`, `AGENT_CRON_MINUTE` (defaults: weekdays **9:35** in `MARKET_TIMEZONE`)

### 2. Frontend (Next.js)

See `client/README.md` if present; otherwise:

- Set **`NEXT_PUBLIC_API_URL`** on Vercel to your **backend** base URL (the Next app proxies `/api/v1/*` to the backend).
- Deploy; open the site, log in, create a portfolio with **real tickers**, open **Model Registry**, retrain if needed, then open a portfolio dashboard.

### 3. Ticker search

Search prefers Yahoo, then Alpha Vantage **SYMBOL_SEARCH**. Pick the **symbol** from the dropdown (e.g. Google → `GOOGL`). Long uppercase words alone are **not** accepted as manual symbols to avoid storing `AMAZON` instead of `AMZN`.

---

## Agent schedule: “Next run in 12h …” — is it only once per day?

**By default, yes:** the in-process scheduler runs the agent **once per US trading weekday** at the time you configure (`AGENT_CRON_HOUR` / `AGENT_CRON_MINUTE` in `MARKET_TIMEZONE`). The UI countdown is the time until that **next cron** fire.

You can always:

- Click **Run Now** for an immediate run (does not replace the cron; it adds a manual run).
- Set `AGENT_CRON_ENABLED=false` on the server if you only want manual runs.

**Note:** On free-tier hosts, the service may **sleep**. In-process crons only run while the process is awake; use `RENDER_EXTERNAL_URL` + keep-alive or an external cron hitting your API if you need reliability without upgrading.

---

## Repo layout

| Path | Role |
|------|------|
| `server/` | FastAPI API, ML training, agent, scheduler |
| `client/` | Next.js dashboard |
| `IDEA.md` | Original product vision and stack notes |
| `render.yaml` | Example Render Docker blueprint |

---

## Contributing / support

Open issues with: host (Render/Railway/local), whether `STOOQ_API_KEY` and DB are set, and one failing request path (e.g. `GET /api/v1/dashboard/{id}`). That keeps debugging fast.

---

*Paper trading only. Not financial advice.*
