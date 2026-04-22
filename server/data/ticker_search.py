from __future__ import annotations

import asyncio
import re

import httpx
import yfinance as yf

from core.config import settings
from data.exceptions import MarketDataUnavailableError
from data.market_data import get_current_price

COMMON_TICKERS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "exchange": "NASDAQ", "type": "stock"},
    {"ticker": "INTC", "name": "Intel Corp.", "exchange": "NASDAQ", "type": "stock"},
]
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{1,9}$")


def _manual_symbol_candidate(query: str) -> list[dict]:
    raw = query.strip()
    if raw != raw.upper():
        return []

    symbol = raw.upper()
    if not SYMBOL_PATTERN.fullmatch(symbol):
        return []
    # Avoid accepting plain company names like AMAZON/GOOGLE/WALMART
    # as manual symbols when provider search is temporarily unavailable.
    if "." not in symbol and "-" not in symbol and len(symbol) > 5:
        return []

    return [
        {
            "ticker": symbol,
            "name": symbol,
            "exchange": "Manual",
            "type": "symbol",
        }
    ]


def _search_sync(query: str, limit: int) -> list[dict]:
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
                    "name": quote.get("shortname")
                    or quote.get("longname")
                    or symbol.upper(),
                    "exchange": quote.get("exchange") or quote.get("exchDisp") or "",
                    "type": quote.get("quoteType") or "stock",
                }
            )

        return rows[:limit]
    except Exception:
        return []


def _alpha_vantage_symbol_search_sync(query: str, limit: int) -> list[dict]:
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


async def search_tickers(query: str, limit: int = 10) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    rows = await asyncio.to_thread(_search_sync, query, max(1, limit))
    if rows:
        return rows
    rows = await asyncio.to_thread(_alpha_vantage_symbol_search_sync, query, max(1, limit))
    if rows:
        return rows

    manual = _manual_symbol_candidate(query)
    if manual:
        return manual[:limit]

    if not settings.ALLOW_SEARCH_FALLBACK_TICKERS:
        return []

    query_upper = query.upper()
    fallback = [
        item
        for item in COMMON_TICKERS
        if query_upper in item["ticker"] or query.lower() in item["name"].lower()
    ]
    return fallback[:limit]


async def validate_ticker(ticker: str) -> bool:
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
