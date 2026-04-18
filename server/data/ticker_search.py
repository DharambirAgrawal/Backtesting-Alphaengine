from __future__ import annotations

import asyncio

import yfinance as yf

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


async def search_tickers(query: str, limit: int = 10) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    rows = await asyncio.to_thread(_search_sync, query, max(1, limit))
    if rows:
        return rows

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
    except Exception:
        return False
