# AlphaEngine
### Autonomous AI Paper Trading System

---

## What Is This?

AlphaEngine is an intelligent paper trading system that autonomously manages virtual stock portfolios using real market data, machine learning models, and an AI agent that thinks, reasons, and makes trading decisions — all without any real money involved.

You set it up once. You give it a portfolio name, a virtual starting amount (say $10,000), and a list of companies you want it to trade. Then you walk away. Every trading day, at market open, midday, and end of day, the AI wakes up, studies the market, consults its trained ML models, reads the latest news, and decides whether to buy, sell, or hold — just like a real fund manager would. A week later, a month later, you open the dashboard and see exactly how it performed, every decision it made, and why it made them.

This is not a simple "buy low sell high" script. The system combines multiple layers of intelligence — trained neural networks, gradient boosting classifiers, technical analysis signals, and news sentiment — and hands all of that information to a large language model that reasons over it and makes a final call. Every trade is logged with the agent's full reasoning. You can read exactly why it bought Apple at $189 on a Tuesday morning.

---

## The Problem It Solves

Learning quantitative finance and algorithmic trading is hard because:

- Real trading requires real money and real risk
- Most backtesting tools are either too simple (spreadsheets) or too complex (institutional platforms)
- There's no good way to see *why* an algorithm made a decision — just that it did
- Setting up ML pipelines for financial data takes weeks of boilerplate

AlphaEngine gives you a production-grade system that does all of this, runs on free infrastructure, and shows you everything — the decisions, the reasoning, the model accuracy, the profit and loss — in a clean dashboard you can open from your phone.

---

## How It Works

### The Three-Layer Intelligence Stack

```
Layer 1 — Data
  Real-time prices and search from Finnhub (primary), Yahoo Finance (secondary)
  Company news headlines from NewsAPI
  Daily OHLCV data from Stooq (historical) and Yahoo (current)
  Technical indicators computed on live data (RSI, MACD, Bollinger Bands)

Layer 2 — Machine Learning Models
  LSTM neural network   → predicts future price (trained per company)
  XGBoost classifier    → predicts direction: up or down (trained per company)
  Technical signals     → RSI overbought/oversold, MACD crossovers, Bollinger squeezes

Layer 3 — AI Agent (Gemini 1.5 Flash)
  Receives portfolio state + market context
  Calls ML models as tools to gather predictions
  Reads news sentiment
  Reasons over all signals
  Decides: BUY, SELL, or HOLD
  Executes the trade and logs its full reasoning
```

The key design principle: **the AI agent does not predict prices directly.** It only reasons. The ML models do the predicting. The agent reads those predictions like a fund manager reads analyst reports, then makes a judgment call. This separation makes the system more accurate, more interpretable, and more interesting to show in an interview.

### A Real Example of What Happens

```
9:35 AM — Market opens. Agent wakes up for Portfolio "Tech Aggressive".

Agent calls: get_portfolio_status()
→ Cash: $7,234  |  Holdings: AAPL 2 shares, NVDA 1 share  |  Total: $10,180

Agent calls: predict_price("TSLA", horizon=5)
→ LSTM predicts: $195.40 in 5 days (currently $189.10) — confidence 68%

Agent calls: classify_direction("TSLA")
→ XGBoost: UP with 71% probability

Agent calls: get_technical_signals("TSLA")
→ RSI: 44 (neutral), MACD: bullish crossover yesterday, BB: mid-band

Agent calls: get_sentiment_score("TSLA")
→ News sentiment: +0.55 (positive — earnings beat mentioned in 3 headlines)

Agent reasons:
"LSTM predicts +3.3% upside. XGBoost agrees with 71% confidence.
MACD bullish crossover is a strong technical signal. Sentiment is
positive post-earnings. RSI is not overbought so there is room to run.
Allocating 4% of portfolio ($408) to TSLA."

Agent calls: execute_trade("TSLA", "BUY", amount_usd=408)
→ Trade executed: 2.15 shares @ $189.77

Trade logged to database with full reasoning.
You see it in the dashboard 10 seconds later.
```

---

## What You Can Do With It

### Multiple Independent Portfolios
Create as many portfolios as you want, each completely separate:

| Portfolio | Capital | Companies | Strategy |
|-----------|---------|-----------|----------|
| Tech Aggressive | $10,000 | AAPL, TSLA, NVDA, META | High-risk growth |
| Defensive Mix | $5,000 | JNJ, KO, PG, BRK.B | Stable blue chips |
| My Watchlist | $25,000 | Any 20 companies | Experimental |

Each portfolio has its own ML models trained specifically on its companies, its own agent runs, its own P&L history, and its own dashboard view.

### Search Any Public Company
The dashboard has a live company search. Type "Apple" and you get AAPL. Type "Saudi Aramco" and you get ARAMCO. Any publicly traded stock on NYSE or NASDAQ works. The system trains a model for it automatically when you add it.

### Full Trade History With Reasoning
Every single trade is stored with:
- The exact price and timestamp
- How many shares were bought or sold
- The complete AI reasoning paragraph
- Which ML tools were called and what they returned
- Whether the trade was profitable (tracked after the fact)

### Performance Analytics
After a week or month of running, you can see:
- Total return vs starting capital
- Sharpe ratio (risk-adjusted return)
- Maximum drawdown (worst dip from peak)
- Win rate (what percentage of trades were profitable)
- Best and worst individual trades
- Portfolio value chart over time

### ML Model Health
See the accuracy of every trained model:
- AAPL LSTM: 68% accurate on 5-day price direction
- TSLA XGBoost: 61% accurate on 3-day up/down classification
- Retrain any model manually or let the system retrain automatically when accuracy drops

---

## The Technology Stack

### Backend — Python on Render
The brain of the system. A FastAPI server that runs the agent, trains ML models, fetches market data, and exposes a REST API.

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web framework | FastAPI | REST API, async request handling |
| Database | PostgreSQL (Render) | All trades, portfolios, users |
| Model storage | Supabase Storage | Trained ML model files |
| AI agent | Gemini 1.5 Flash | Decision making and reasoning |
| Primary Market API| Finnhub | High-speed ticker search and real-time quotes |
| Fallback Data | yfinance + Stooq | Daily historical OHLCV data and fallback quoting |
| News data | NewsAPI | Headlines per ticker |
| ML — neural net | PyTorch LSTM | Price prediction |
| ML — classifier | XGBoost | Direction classification |
| Technical analysis | ta (Python library) | RSI, MACD, Bollinger Bands |
| Scheduler | APScheduler | Cron jobs, keep-alive |
| Auth | python-jose + bcrypt | JWT tokens, password hashing |
| Hosting | Render (free tier) | Always-on Python server |

### Frontend — Next.js on Vercel
The dashboard you actually look at. Built with Next.js and designed to feel like a real fintech product.

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Next.js 14 (App Router) | Pages, routing, SSR |
| Language | TypeScript | Type safety across all API calls |
| Styling | Tailwind CSS + shadcn/ui | Dark financial dashboard aesthetic |
| Charts | Recharts | Portfolio value, accuracy history |
| Auth | JWT (cookie + localStorage) | Session management, route protection |
| Hosting | Vercel (free tier) | Global CDN, instant deploys |
| UI generation | v0 by Vercel | Rapid component scaffolding |

### Infrastructure
Everything runs on free tiers:

| Service | What It Stores | Free Limit | Usage |
|---------|---------------|------------|-------|
| Render | Python backend | 512MB RAM | Well within |
| Render Postgres | All app data | 1GB storage | ~50MB for heavy use |
| Supabase Storage | ML model files | 1GB storage | ~25MB for 10 tickers |
| Vercel | Frontend | Unlimited hobby | — |
| Gemini API | — (API calls) | 1M tokens/day | ~500 trades/day |
| yfinance | — (API calls) | Unlimited | Free forever |
| NewsAPI | — (API calls) | 100 req/day | Enough for 10 tickers |

**Zero monthly cost.** Everything runs free.

---

## How Models Learn Over Time

This is the most technically interesting part of the system.

When the agent makes a trade, it records what the ML model predicted and what actually happened. Every Sunday at 2 AM, the system retrains all active models — but this time, the training data includes the real outcomes of past predictions. Bad predictions become training examples. The model literally learns from its own mistakes over time.

This technique is called **walk-forward validation** and it is a standard practice in quantitative finance. The model never trains on future data (which would be cheating). It only learns from the past, then predicts the future, and then incorporates those outcomes into the next training cycle.

Additionally, if a model's rolling 7-day accuracy drops below 52% (barely better than random), the system automatically triggers a retrain immediately — it doesn't wait for Sunday.

```
Week 1: TSLA LSTM trained on 2 years of historical data
Week 2: Retrain includes 1 week of live predictions vs actual outcomes
Week 3: Retrain includes 2 weeks of live outcomes
...
Month 3: Model has learned from 3 months of its own mistakes
```

---

## Security

The system uses a simple but complete authentication system:

- **Your credentials are set once** via environment variables when you deploy the backend. Your email and hashed password are seeded directly into the database. No sign-up flow, no third-party auth service.
- **JWT tokens** are issued on login and expire after 7 days. Every API request requires a valid token.
- **Role-based access**: you are the admin. You can create other user accounts from the dashboard, give them access, and delete them at any time. Regular users can view the dashboards but cannot manage users.
- **Passwords are never stored in plain text** — bcrypt hashing with salt, the industry standard.
- **Route protection** at the Next.js middleware level — unauthenticated users are redirected to `/login` before any page renders.

---

## Deployment Architecture

```
                        ┌─────────────────────┐
                        │   Vercel (Frontend)  │
                        │   Next.js Dashboard  │
                        │   alphaengine.vercel │
                        └──────────┬──────────┘
                                   │ HTTPS + JWT
                        ┌──────────▼──────────┐
                        │   Render (Backend)   │
                        │   FastAPI + Python   │
                        │   APScheduler crons  │
                        └──────┬────────┬──────┘
                               │        │
              ┌────────────────▼──┐  ┌──▼────────────────┐
              │  Render Postgres  │  │  Supabase Storage  │
              │  Users, trades,   │  │  LSTM .pt files    │
              │  portfolios,      │  │  XGBoost .pkl files│
              │  snapshots        │  └───────────────────┘
              └───────────────────┘
                               │
              ┌────────────────▼──────────────────┐
              │         External APIs              │
              │  yfinance · NewsAPI · Gemini API   │
              └───────────────────────────────────┘
```

The backend keeps itself alive with an internal ping every 10 minutes — no external keep-alive service needed.

---

## Build Plan — Two Weekends

### Weekend 1 — The Engine
**Saturday:**
- FastAPI project scaffold + database schema + migrations
- yfinance data fetcher + technical indicators (RSI, MACD, Bollinger)
- Auth system: users table, seed script, JWT middleware, login endpoint

**Sunday:**
- LSTM + XGBoost training pipeline
- Supabase model storage (upload/download)
- Gemini agent loop with all 7 tools wired up
- Test: manually trigger agent on one portfolio, see trade in DB

### Weekend 2 — The Product
**Saturday:**
- APScheduler cron jobs (3x daily + weekly retrain + keep-alive)
- All REST endpoints complete and tested
- Frontend scaffold in Next.js — login page, sidebar, routing, auth flow

**Sunday:**
- Dashboard page: value chart, stats, holdings, recent trades
- Transaction history page with filters and reasoning modal
- ML models page
- Deploy backend to Render, frontend to Vercel
- End-to-end test: login → create portfolio → agent runs → see results

---

## Why This Project Is Impressive

This is not a tutorial project. It demonstrates:

**Quant Finance concepts:**
Walk-forward validation, Sharpe ratio, max drawdown, technical indicators, sentiment analysis, multi-signal decision fusion — these are concepts that appear directly in Two Sigma, Citadel, and Jane Street interviews.

**ML Engineering:**
Training, saving, versioning, and reloading models. Feedback loops where model outcomes influence future training. Per-entity models (one per ticker) instead of a naive one-size-fits-all approach.

**Agentic AI architecture:**
The LLM-as-orchestrator pattern where the model calls tools rather than hallucinating answers. Full reasoning traces stored per decision. This is the architecture pattern that serious AI engineering roles care about right now.

**Full-stack systems thinking:**
Free-tier infrastructure design, keeping services alive without paying, async Python, JWT auth, PostgreSQL schema design, REST API design, real-time polling — the full picture from database to browser.

**Product quality:**
A dashboard that looks and feels like a real fintech product, not a side project. Multiple portfolios, search, filters, modals, skeletons, error states — production-grade UI details.

---

## Project Links

| Resource | Location |
|----------|----------|
| Backend spec | `alphaengine-backend-spec.md` |
| Frontend spec | `alphaengine-frontend-spec.md` |
| Backend repo | `alphaengine-backend/` |
| Frontend repo | `alphaengine-frontend/` |
| Live backend | `https://alphaengine.onrender.com` |
| Live frontend | `https://alphaengine.vercel.app` |

---

*Built with Python · FastAPI · PyTorch · XGBoost · Gemini · Next.js · PostgreSQL*
*Deployed on Render + Supabase + Vercel — $0/month*