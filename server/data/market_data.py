from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


def _fallback_price(ticker: str) -> float:
    seed = abs(hash(ticker.upper())) % 400
    return round(50 + seed + (datetime.now(timezone.utc).timetuple().tm_yday % 17), 2)


def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]) for col in df.columns]
    return df


def _synthetic_history(ticker: str, days: int) -> list[dict]:
    base = _fallback_price(ticker)
    rows: list[dict] = []
    now = datetime.now(timezone.utc)

    for i in range(days):
        dt = now - timedelta(days=days - i)
        drift = ((i % 9) - 4) * 0.35
        close = max(1.0, base + drift)
        open_price = max(1.0, close - 0.45)
        high = close + 0.8
        low = max(0.5, close - 1.2)
        volume = float(1_000_000 + (i * 25_000))
        rows.append(
            {
                "date": dt.date().isoformat(),
                "open": round(open_price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": volume,
            }
        )

    return rows


def _history_sync(ticker: str, days: int) -> list[dict]:
    try:
        period = f"{max(days + 2, 5)}d"
        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            return _synthetic_history(ticker, days)

        df = _normalize_ohlcv_columns(df)
        df = df.tail(days)
        rows: list[dict] = []

        for idx, row in df.iterrows():
            ts = pd.Timestamp(idx)
            rows.append(
                {
                    "date": ts.date().isoformat(),
                    "open": float(row.get("Open", 0.0)),
                    "high": float(row.get("High", 0.0)),
                    "low": float(row.get("Low", 0.0)),
                    "close": float(row.get("Close", 0.0)),
                    "volume": float(row.get("Volume", 0.0)),
                }
            )

        return rows if rows else _synthetic_history(ticker, days)
    except Exception:
        return _synthetic_history(ticker, days)


async def get_history(ticker: str, days: int = 30) -> list[dict]:
    return await asyncio.to_thread(_history_sync, ticker.upper(), max(days, 1))


async def get_current_price(ticker: str) -> float:
    rows = await get_history(ticker, days=2)
    if rows:
        return float(rows[-1]["close"])
    return _fallback_price(ticker)


async def get_price_snapshot(ticker: str) -> dict:
    rows = await get_history(ticker, days=2)
    if len(rows) >= 2:
        last = float(rows[-1]["close"])
        prev = float(rows[-2]["close"])
    elif rows:
        last = float(rows[-1]["close"])
        prev = last
    else:
        last = _fallback_price(ticker)
        prev = last

    change = last - prev
    change_pct = (change / prev * 100) if prev else 0.0

    return {
        "ticker": ticker.upper(),
        "price": round(last, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _ohlcv_sync(ticker: str, period: str = "2y") -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()

    df = _normalize_ohlcv_columns(df)
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    })
    return df


async def get_ohlcv_dataframe(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        df = await asyncio.to_thread(_ohlcv_sync, ticker.upper(), period)
        return df
    except Exception:
        return pd.DataFrame()
