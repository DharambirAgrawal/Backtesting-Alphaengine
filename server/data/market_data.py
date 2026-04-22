from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd
import yfinance as yf

from core.config import settings
from data.exceptions import MarketDataUnavailableError

for _log in ("yfinance", "yfinance.base", "yfinance.ticker", "yfinance.scrapers"):
    logging.getLogger(_log).setLevel(logging.ERROR)


def _fallback_price(ticker: str) -> float:
    seed = abs(hash(ticker.upper())) % 400
    return round(50 + seed + (datetime.now(timezone.utc).timetuple().tm_yday % 17), 2)


def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]) for col in df.columns]
    return df


def _period_to_max_days(period: str) -> int:
    p = period.strip().lower()
    if p.endswith("y"):
        try:
            return int(float(p[:-1]) * 365)
        except ValueError:
            return 730
    if p.endswith("mo"):
        try:
            return int(float(p[:-2]) * 31)
        except ValueError:
            return 180
    if p.endswith("d"):
        try:
            return int(p[:-1])
        except ValueError:
            return 30
    return 730


def _standardize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = _normalize_ohlcv_columns(df)
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    out = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    if "close" not in out.columns:
        return pd.DataFrame()
    return out


def _yahoo_history_dataframe(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Prefer Ticker.history — often succeeds when yf.download hits quote JSON errors."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d", auto_adjust=False)
        df = _standardize_ohlcv_df(df)
        return df if not df.empty else pd.DataFrame()
    except (json.JSONDecodeError, ValueError, KeyError, OSError):
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _yahoo_download_dataframe(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        return _standardize_ohlcv_df(df)
    except Exception:
        return pd.DataFrame()


def _stooq_daily_sync(ticker: str) -> pd.DataFrame:
    """Daily OHLCV CSV from Stooq. Requires STOOQ_API_KEY (free, get from stooq.com)."""
    key = settings.STOOQ_API_KEY
    if not key:
        return pd.DataFrame()

    raw_sym = ticker.strip().upper().replace("/", ".")
    if "." not in raw_sym:
        raw_sym = f"{raw_sym.lower()}.us"
    else:
        raw_sym = raw_sym.lower()
    url = f"https://stooq.com/q/d/l/?s={raw_sym}&i=d&apikey={key}"
    try:
        df = pd.read_csv(url)
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"date", "open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    vol_series = (
        pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
        if "volume" in df.columns
        else pd.Series(0.0, index=df.index)
    )
    frame = pd.DataFrame(
        {
            "open": pd.to_numeric(df["open"], errors="coerce"),
            "high": pd.to_numeric(df["high"], errors="coerce"),
            "low": pd.to_numeric(df["low"], errors="coerce"),
            "close": pd.to_numeric(df["close"], errors="coerce"),
            "volume": vol_series,
        }
    )
    frame.index = pd.to_datetime(df["date"], utc=True)
    frame = frame.sort_index().dropna(subset=["close"])
    max_days = _period_to_max_days("5y")
    if len(frame) > max_days:
        frame = frame.tail(max_days)
    return frame


def _alpha_vantage_daily_sync(ticker: str) -> pd.DataFrame:
    key = settings.ALPHA_VANTAGE_KEY
    if not key:
        return pd.DataFrame()

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker.upper(),
        "outputsize": "full",
        "apikey": key,
    }
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception:
        return pd.DataFrame()

    if not isinstance(payload, dict):
        return pd.DataFrame()
    if payload.get("Note") or payload.get("Error Message"):
        return pd.DataFrame()

    series = payload.get("Time Series (Daily)") or payload.get("daily") or {}
    if not isinstance(series, dict) or not series:
        return pd.DataFrame()

    rows: list[dict] = []
    for date_str, bar in series.items():
        if not isinstance(bar, dict):
            continue
        try:
            rows.append(
                {
                    "date": date_str,
                    "open": float(bar.get("1. open") or 0),
                    "high": float(bar.get("2. high") or 0),
                    "low": float(bar.get("3. low") or 0),
                    "close": float(bar.get("4. close") or 0),
                    "volume": float(bar.get("5. volume") or 0),
                }
            )
        except (TypeError, ValueError):
            continue

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    frame = frame.set_index("date").sort_index()
    max_days = _period_to_max_days("5y")
    if len(frame) > max_days:
        frame = frame.tail(max_days)
    return frame


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


def _daily_ohlcv_first_hit(ticker: str, period: str) -> pd.DataFrame:
    """Try providers in order. Stooq-first avoids Yahoo IP blocks (same path for fills + marks)."""
    seq: list[tuple[str, object]] = []
    if settings.STOOQ_FIRST:
        seq.append(("stooq", lambda: _stooq_daily_sync(ticker)))
    seq.extend(
        [
            ("yahoo_history", lambda: _yahoo_history_dataframe(ticker, period=period)),
            ("yahoo_download", lambda: _yahoo_download_dataframe(ticker, period=period)),
        ]
    )
    if not settings.STOOQ_FIRST:
        seq.append(("stooq", lambda: _stooq_daily_sync(ticker)))
    seq.append(("alpha_vantage", lambda: _alpha_vantage_daily_sync(ticker)))

    for _, fn in seq:
        df = fn()
        if df is not None and not df.empty:
            return df
    return pd.DataFrame()


def _fetch_ohlcv_chain(ticker: str, period: str = "2y") -> pd.DataFrame:
    return _daily_ohlcv_first_hit(ticker, period)


def _empty_chain_message(ticker: str) -> str:
    return (
        f"No real OHLCV returned for {ticker} from Stooq, Yahoo, or Alpha Vantage. "
        "When the US cash equity session is closed or on holidays, daily feeds still "
        "expose the **last completed session** close — fix network/API access or set "
        "ALLOW_SYNTHETIC_MARKET_DATA=true only for offline dev."
    )


def _history_sync(ticker: str, days: int) -> list[dict]:
    period = f"{max(days + 5, 7)}d"

    try:
        df = _daily_ohlcv_first_hit(ticker, period)

        if df is None or df.empty:
            if settings.ALLOW_SYNTHETIC_MARKET_DATA:
                return _synthetic_history(ticker, days)
            raise MarketDataUnavailableError(_empty_chain_message(ticker))

        df = df.tail(days)
        rows: list[dict] = []

        for idx, row in df.iterrows():
            ts = pd.Timestamp(idx)
            rows.append(
                {
                    "date": ts.date().isoformat(),
                    "open": float(row.get("open", row.get("Open", 0.0))),
                    "high": float(row.get("high", row.get("High", 0.0))),
                    "low": float(row.get("low", row.get("Low", 0.0))),
                    "close": float(row.get("close", row.get("Close", 0.0))),
                    "volume": float(row.get("volume", row.get("Volume", 0.0))),
                }
            )

        if rows:
            return rows
        if settings.ALLOW_SYNTHETIC_MARKET_DATA:
            return _synthetic_history(ticker, days)
        raise MarketDataUnavailableError(_empty_chain_message(ticker))
    except MarketDataUnavailableError:
        raise
    except Exception as exc:
        if settings.ALLOW_SYNTHETIC_MARKET_DATA:
            return _synthetic_history(ticker, days)
        raise MarketDataUnavailableError(_empty_chain_message(ticker)) from exc


async def get_history(ticker: str, days: int = 30) -> list[dict]:
    return await asyncio.to_thread(_history_sync, ticker.upper(), max(days, 1))


async def get_current_price(ticker: str) -> float:
    rows = await get_history(ticker, days=2)
    if rows:
        return float(rows[-1]["close"])
    if settings.ALLOW_SYNTHETIC_MARKET_DATA:
        return _fallback_price(ticker)
    raise MarketDataUnavailableError(_empty_chain_message(ticker))


async def get_price_snapshot(ticker: str) -> dict:
    rows = await get_history(ticker, days=2)
    if len(rows) >= 2:
        last = float(rows[-1]["close"])
        prev = float(rows[-2]["close"])
    elif rows:
        last = float(rows[-1]["close"])
        prev = last
    else:
        if settings.ALLOW_SYNTHETIC_MARKET_DATA:
            last = _fallback_price(ticker)
            prev = last
        else:
            raise MarketDataUnavailableError(_empty_chain_message(ticker))

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
    return _fetch_ohlcv_chain(ticker, period=period)


async def get_ohlcv_dataframe(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        df = await asyncio.to_thread(_ohlcv_sync, ticker.upper(), period)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
