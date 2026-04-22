from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_current_user
from core.schemas import NewsItemOut, PriceDataOut, PriceHistoryBarOut, TickerSearchResultOut
from core.models import User
from data.exceptions import MarketDataUnavailableError
from data.market_data import get_history, get_price_snapshot
from data.news_fetcher import get_news
from data.ticker_search import search_tickers

router = APIRouter(tags=["market"])


@router.get("/market/search", response_model=list[TickerSearchResultOut])
async def market_search(
    q: str = Query(min_length=1),
    _: User = Depends(get_current_user),
):
    rows = await search_tickers(q, limit=20)
    return [TickerSearchResultOut(**item) for item in rows]


@router.get("/market/price/{ticker}", response_model=PriceDataOut)
async def market_price(ticker: str, _: User = Depends(get_current_user)):
    try:
        payload = await get_price_snapshot(ticker)
        return PriceDataOut(**payload)
    except MarketDataUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/market/history/{ticker}", response_model=list[PriceHistoryBarOut])
async def market_history(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365),
    _: User = Depends(get_current_user),
):
    try:
        rows = await get_history(ticker, days=days)
        return [PriceHistoryBarOut(**item) for item in rows]
    except MarketDataUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/market/news/{ticker}", response_model=list[NewsItemOut])
async def market_news(
    ticker: str,
    _: User = Depends(get_current_user),
):
    rows = await get_news(ticker, limit=10)
    return [NewsItemOut(**item) for item in rows]
