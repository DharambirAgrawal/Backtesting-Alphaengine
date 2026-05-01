from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from newsapi import NewsApiClient

from core.config import settings, ALLOW_SYNTHETIC_NEWS

# Real headlines only unless ALLOW_SYNTHETIC_NEWS=true (offline demos).

POSITIVE_WORDS = {
    "beat",
    "growth",
    "up",
    "surge",
    "gain",
    "record",
    "strong",
    "bull",
    "upgrade",
}
NEGATIVE_WORDS = {
    "miss",
    "drop",
    "down",
    "lawsuit",
    "weak",
    "bear",
    "downgrade",
    "loss",
    "cut",
}

news_client = NewsApiClient(api_key=settings.NEWS_API_KEY) if settings.NEWS_API_KEY else None


def _fallback_news(ticker: str, limit: int) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "title": f"{ticker.upper()} market update",
            "source": "AlphaEngine",
            "url": f"https://finance.yahoo.com/quote/{ticker.upper()}",
            "published_at": now,
            "sentiment": 0.0,
        }
        for _ in range(limit)
    ]


def _fetch_news_sync(ticker: str, limit: int) -> list[dict]:
    if not news_client:
        return _fallback_news(ticker, limit) if ALLOW_SYNTHETIC_NEWS else []

    try:
        payload = news_client.get_everything(
            q=ticker.upper(),
            language="en",
            sort_by="publishedAt",
            page_size=limit,
        )
        articles = payload.get("articles", [])
        if not articles:
            return _fallback_news(ticker, limit) if ALLOW_SYNTHETIC_NEWS else []

        rows: list[dict] = []
        for article in articles:
            rows.append(
                {
                    "title": article.get("title") or f"{ticker.upper()} update",
                    "source": (article.get("source") or {}).get("name") or "Unknown",
                    "url": article.get("url") or "",
                    "published_at": article.get("publishedAt")
                    or datetime.now(timezone.utc).isoformat(),
                    "sentiment": None,
                }
            )

        return rows
    except Exception:
        return _fallback_news(ticker, limit) if ALLOW_SYNTHETIC_NEWS else []


async def get_news(ticker: str, limit: int = 5) -> list[dict]:
    return await asyncio.to_thread(_fetch_news_sync, ticker.upper(), max(1, limit))


def _score_text(text: str) -> float:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return 0.0

    positive = sum(1 for word in words if word in POSITIVE_WORDS)
    negative = sum(1 for word in words if word in NEGATIVE_WORDS)

    score = (positive - negative) / max(len(words), 8)
    return max(-1.0, min(1.0, score * 5))


async def get_sentiment_score(ticker: str) -> dict:
    news_items = await get_news(ticker, limit=8)
    if not news_items:
        return {"score": 0.0, "headlines": []}

    scores = [_score_text(item.get("title", "")) for item in news_items]
    avg_score = round(sum(scores) / len(scores), 4)
    headlines = [item.get("title", "") for item in news_items[:3] if item.get("title")]

    return {"score": avg_score, "headlines": headlines}
