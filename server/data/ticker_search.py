from __future__ import annotations

import asyncio
import re

import httpx
import yfinance as yf

from core.config import settings
from data.exceptions import MarketDataUnavailableError
from data.market_data import get_current_price

SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{1,9}$")

# ---------------------------------------------------------------------------
# Provider 1: Finnhub Symbol Lookup  (primary — free, 60 req/min)
# Docs: https://finnhub.io/docs/api/symbol-lookup
# Returns displaySymbol, description, type — fast and reliable
# ---------------------------------------------------------------------------

def _finnhub_search_sync(query: str, limit: int) -> list[dict]:
    key = settings.FINNHUB_API_KEY
    if not key:
        return []

    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.get(
                "https://finnhub.io/api/v1/search",
                params={"q": query, "token": key},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    if not isinstance(payload, dict):
        return []

    matches = payload.get("result", [])
    rows: list[dict] = []
    for item in matches:
        symbol = str(item.get("displaySymbol") or item.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        description = str(item.get("description") or symbol).strip()
        item_type = str(item.get("type") or "stock").strip().lower()
        rows.append(
            {
                "ticker": symbol,
                "name": description,
                "exchange": "",  # Finnhub basic search doesn't return exchange on free tier
                "type": item_type if item_type else "stock",
            }
        )

    return rows[:limit]


# ---------------------------------------------------------------------------
# Provider 2: Yahoo Finance Search  (secondary — unofficial, good coverage)
# ---------------------------------------------------------------------------

def _yahoo_search_sync(query: str, limit: int) -> list[dict]:
    try:
        search = yf.Search(query=query, max_results=limit)
        quotes = getattr(search, "quotes", []) or []
        rows: list[dict] = []

        for quote in quotes:
            symbol = quote.get("symbol")
            if not symbol:
                continue
            rows.append(
                {
                    "ticker": symbol.upper(),
                    "name": quote.get("shortname") or quote.get("longname") or symbol.upper(),
                    "exchange": quote.get("exchange") or quote.get("exchDisp") or "",
                    "type": quote.get("quoteType") or "stock",
                }
            )

        return rows[:limit]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Provider 3: Alpha Vantage Symbol Search  (tertiary — official free tier)
# 25 req/day on free plan — used only when Finnhub + Yahoo both fail
# ---------------------------------------------------------------------------

def _alpha_vantage_search_sync(query: str, limit: int) -> list[dict]:
    key = settings.ALPHA_VANTAGE_KEY
    if not key:
        return []

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "SYMBOL_SEARCH",
                    "keywords": query,
                    "apikey": key,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    matches = payload.get("bestMatches", []) if isinstance(payload, dict) else []
    rows: list[dict] = []
    for item in matches:
        symbol = str(item.get("1. symbol", "")).strip().upper()
        if not symbol:
            continue
        rows.append(
            {
                "ticker": symbol,
                "name": str(item.get("2. name", symbol)).strip(),
                "exchange": str(item.get("4. region", "")).strip(),
                "type": str(item.get("3. type", "stock")).strip().lower() or "stock",
            }
        )

    return rows[:limit]


# ---------------------------------------------------------------------------
# Manual symbol candidate — handles exact uppercase tickers typed by user
# ---------------------------------------------------------------------------

def _manual_symbol_candidate(query: str) -> list[dict]:
    raw = query.strip()
    if raw != raw.upper():
        return []

    symbol = raw.upper()
    if not SYMBOL_PATTERN.fullmatch(symbol):
        return []

    # Avoid treating plain company names (AMAZON, GOOGLE) as manual symbols
    if "." not in symbol and "-" not in symbol and len(symbol) > 5:
        return []

    return [
        {
            "ticker": symbol,
            "name": symbol,
            "exchange": "Unknown",
            "type": "stock",
        }
    ]


# ---------------------------------------------------------------------------
# Ranking + deduplication
# ---------------------------------------------------------------------------

def _rank_and_deduplicate(query: str, rows: list[dict], limit: int) -> list[dict]:
    q = query.strip().upper()
    if not q:
        return rows[:limit]

    # Deduplicate by ticker symbol
    dedup: dict[str, dict] = {}
    for row in rows:
        symbol = str(row.get("ticker", "")).upper().strip()
        if not symbol:
            continue
        if symbol not in dedup:
            dedup[symbol] = row

    def score(row: dict) -> tuple[int, int]:
        ticker = str(row.get("ticker", "")).upper()
        name = str(row.get("name", "")).upper().strip()
        type_ = str(row.get("type", "")).lower()

        s = 0
        if ticker == q:
            s += 1000
        if ticker.startswith(q):
            s += 300
        if q in ticker:
            s += 120
        if q in name:
            s += 100
        if type_ in {"stock", "equity", "etf", "common stock"}:
            s += 30
        # Penalise very short tickers when query is longer (e.g. "AM" vs "AMZN")
        if len(q) >= 3 and len(ticker) <= 2 and ticker != q:
            s -= 220

        length_penalty = abs(len(ticker) - len(q))
        return (s, -length_penalty)

    ranked = sorted(list(dedup.values()), key=score, reverse=True)
    return ranked[:limit]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_tickers(query: str, limit: int = 10) -> list[dict]:
    """
    Search for ticker symbols by name or symbol.

    Pipeline (parallel where safe):
      1. Finnhub symbol search (primary — fast, reliable)
      2. Yahoo Finance search (secondary — broad coverage)
      3. Alpha Vantage symbol search (tertiary — official fallback, rate-limited)
      4. Manual symbol candidate (user typed an exact uppercase symbol)
    """
    query = query.strip()
    if not query:
        return []

    max_fetch = max(1, limit) * 2

    # Run all three live providers concurrently
    finnhub_rows, yahoo_rows, av_rows = await asyncio.gather(
        asyncio.to_thread(_finnhub_search_sync, query, max_fetch),
        asyncio.to_thread(_yahoo_search_sync, query, max_fetch),
        asyncio.to_thread(_alpha_vantage_search_sync, query, max_fetch),
    )

    merged = _rank_and_deduplicate(
        query,
        [*finnhub_rows, *yahoo_rows, *av_rows],
        limit,
    )
    if merged:
        return merged

    # No live results — try manual exact-symbol match
    manual = _manual_symbol_candidate(query)
    if manual:
        return manual[:limit]

    return []


async def validate_ticker(ticker: str) -> bool:
    """Return True if the ticker has a fetchable live price."""
    symbol = ticker.strip().upper()
    if not symbol:
        return False

    try:
        price = await get_current_price(symbol)
        return price > 0
    except MarketDataUnavailableError:
        return False
    except Exception:
        return False
