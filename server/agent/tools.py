from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils import as_float, build_holdings_view, build_portfolio_out, transaction_to_out
from core.models import Holding, Portfolio, Transaction
from data.market_data import get_history, get_price_snapshot
from data.news_fetcher import get_sentiment_score
from ml.features import get_technical_signals
from ml.predictor import classify_direction, predict_price

TOOLS = [
    {
        "name": "predict_price",
        "description": "Uses trained LSTM model to predict price N days ahead. Returns predicted price and confidence score.",
        "parameters": {
            "ticker": "string - stock ticker symbol",
            "horizon_days": "integer - forecast horizon (1-10)",
        },
    },
    {
        "name": "classify_direction",
        "description": "Uses XGBoost to classify if price will go UP or DOWN in next 3 days. Returns direction and probability.",
        "parameters": {
            "ticker": "string",
        },
    },
    {
        "name": "get_technical_signals",
        "description": "Returns RSI, MACD crossover signal, Bollinger Band position for a ticker.",
        "parameters": {
            "ticker": "string",
        },
    },
    {
        "name": "get_sentiment_score",
        "description": "Fetches latest news for ticker, returns sentiment score from -1.0 to 1.0.",
        "parameters": {
            "ticker": "string",
        },
    },
    {
        "name": "get_portfolio_status",
        "description": "Returns current cash, holdings, total value, and unrealized P&L for the portfolio.",
        "parameters": {},
    },
    {
        "name": "execute_trade",
        "description": "Execute a BUY or SELL order. For BUY: specify dollar amount. For SELL: specify shares or 'all'.",
        "parameters": {
            "ticker": "string",
            "action": "string - 'BUY' or 'SELL'",
            "amount_usd": "number - dollar amount for BUY (optional)",
            "shares": "number or 'all' - for SELL (optional)",
        },
    },
    {
        "name": "get_price_history",
        "description": "Returns OHLCV price history for a ticker.",
        "parameters": {
            "ticker": "string",
            "days": "integer - lookback days (default 30)",
        },
    },
]


async def predict_price_tool(ticker: str, horizon_days: int = 3) -> dict:
    return await predict_price(ticker=ticker.upper(), horizon_days=max(1, min(10, horizon_days)))


async def classify_direction_tool(ticker: str) -> dict:
    return await classify_direction(ticker=ticker.upper())


async def get_technical_signals_tool(ticker: str) -> dict:
    return await get_technical_signals(ticker=ticker.upper())


async def get_sentiment_score_tool(ticker: str) -> float:
    return await get_sentiment_score(ticker=ticker.upper())


async def get_price_history_tool(ticker: str, days: int = 30) -> list[dict]:
    return await get_history(ticker=ticker.upper(), days=max(1, days))


async def get_portfolio_status_tool(db: AsyncSession, portfolio_id: str) -> dict:
    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("Portfolio not found")

    holdings, holdings_value = await build_holdings_view(db, portfolio_id)
    current_cash = as_float(portfolio.current_cash)

    return {
        "portfolio_id": str(portfolio.id),
        "current_cash": round(current_cash, 2),
        "holdings_value": round(holdings_value, 2),
        "total_value": round(current_cash + holdings_value, 2),
        "holdings": [item.model_dump() for item in holdings],
    }


async def execute_trade(
    db: AsyncSession,
    portfolio_id: str,
    ticker: str,
    action: str,
    amount_usd: float | None = None,
    shares: float | str | None = None,
    llm_reasoning: str | None = None,
    tools_called: dict | None = None,
) -> dict:
    symbol = ticker.upper().strip()
    action = action.upper().strip()

    if action not in {"BUY", "SELL", "HOLD"}:
        raise ValueError("Invalid action")

    portfolio = await db.get(Portfolio, portfolio_id)
    if not portfolio:
        raise ValueError("Portfolio not found")

    price_payload = await get_price_snapshot(symbol)
    price = float(price_payload["price"])

    holding_stmt = select(Holding).where(
        Holding.portfolio_id == portfolio.id,
        Holding.ticker == symbol,
    )
    holding = await db.scalar(holding_stmt)

    if not holding:
        holding = Holding(
            portfolio_id=portfolio.id,
            ticker=symbol,
            shares=0,
            avg_buy_price=price,
        )
        db.add(holding)

    executed_shares = 0.0
    trade_value = 0.0

    if action == "BUY":
        cash_available = as_float(portfolio.current_cash)
        amount = float(amount_usd) if amount_usd is not None else min(cash_available * 0.05, cash_available)
        amount = min(amount, cash_available)

        if amount <= 0:
            raise ValueError("Insufficient cash for BUY")

        executed_shares = amount / price
        existing_shares = as_float(holding.shares)
        existing_avg = as_float(holding.avg_buy_price)

        new_total_shares = existing_shares + executed_shares
        if new_total_shares > 0:
            holding.avg_buy_price = (
                (existing_shares * existing_avg) + (executed_shares * price)
            ) / new_total_shares

        holding.shares = new_total_shares
        portfolio.current_cash = cash_available - amount
        trade_value = amount

    elif action == "SELL":
        existing_shares = as_float(holding.shares)
        if existing_shares <= 0:
            raise ValueError(f"No shares available to sell for {symbol}")

        if shares == "all" or shares is None:
            executed_shares = existing_shares
        else:
            requested = float(shares)
            executed_shares = max(0.0, min(requested, existing_shares))

        if executed_shares <= 0:
            raise ValueError("No valid shares specified for SELL")

        trade_value = executed_shares * price
        holding.shares = max(0.0, existing_shares - executed_shares)
        if as_float(holding.shares) == 0:
            holding.avg_buy_price = None

        portfolio.current_cash = as_float(portfolio.current_cash) + trade_value

    else:  # HOLD
        executed_shares = 0.0
        trade_value = 0.0

    tx = Transaction(
        portfolio_id=portfolio.id,
        ticker=symbol,
        action=action,
        shares=round(executed_shares, 6),
        price_at_trade=round(price, 4),
        total_value=round(trade_value, 2),
        llm_reasoning=llm_reasoning or "No detailed reasoning provided.",
        tools_called=tools_called or {},
        executed_at=datetime.now(timezone.utc),
    )

    db.add(tx)
    portfolio.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(tx)

    portfolio_out = await build_portfolio_out(db, portfolio)

    return {
        "transaction": transaction_to_out(tx).model_dump(),
        "portfolio": portfolio_out.model_dump(),
    }


async def execute_tool_call(
    db: AsyncSession,
    portfolio_id: str,
    name: str,
    arguments: dict,
):
    if name == "predict_price":
        return await predict_price_tool(
            ticker=str(arguments.get("ticker", "")),
            horizon_days=int(arguments.get("horizon_days", 3)),
        )
    if name == "classify_direction":
        return await classify_direction_tool(ticker=str(arguments.get("ticker", "")))
    if name == "get_technical_signals":
        return await get_technical_signals_tool(ticker=str(arguments.get("ticker", "")))
    if name == "get_sentiment_score":
        return await get_sentiment_score_tool(ticker=str(arguments.get("ticker", "")))
    if name == "get_portfolio_status":
        return await get_portfolio_status_tool(db, portfolio_id)
    if name == "execute_trade":
        return await execute_trade(
            db=db,
            portfolio_id=portfolio_id,
            ticker=str(arguments.get("ticker", "")),
            action=str(arguments.get("action", "HOLD")),
            amount_usd=arguments.get("amount_usd"),
            shares=arguments.get("shares"),
        )
    if name == "get_price_history":
        return await get_price_history_tool(
            ticker=str(arguments.get("ticker", "")),
            days=int(arguments.get("days", 30)),
        )

    raise ValueError(f"Unknown tool call: {name}")
