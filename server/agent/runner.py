from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from agent.prompts import build_context
from agent.tools import (
    classify_direction_tool,
    execute_trade,
    get_portfolio_status_tool,
    get_sentiment_score_tool,
    get_technical_signals_tool,
    predict_price_tool,
)
from api.utils import build_holdings_view, build_portfolio_out, get_portfolio_tickers, snapshot_portfolio
from core.database import SessionLocal
from core.models import AgentRun, Portfolio
from data.market_data import get_current_price
from ml.evaluator import record_prediction


def _build_reasoning(
    ticker: str,
    prediction: dict,
    direction: dict,
    technical: dict,
    sentiment: float,
    action: str,
) -> str:
    return (
        f"{ticker}: Predicted {prediction.get('predicted_price')} in {prediction.get('horizon_days')}d "
        f"(conf {prediction.get('confidence')}). Direction={direction.get('direction')} "
        f"(p={direction.get('probability')}). RSI={technical.get('rsi')}, "
        f"MACD={technical.get('macd')}, sentiment={sentiment}. Action={action}."
    )


async def _with_retries(
    coro,
    *args,
    retries: int = 2,
    base_delay_seconds: float = 0.6,
    **kwargs,
):
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await coro(*args, **kwargs)
        except Exception as exc:  # noqa: PERF203
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(base_delay_seconds * (attempt + 1))

    if last_error:
        raise last_error
    raise RuntimeError("Retry helper reached an unexpected state")


async def _load_or_create_run(
    portfolio_id: str,
    session: str,
    run_type: str,
    run_id: str | None,
):
    async with SessionLocal() as db:
        run: AgentRun | None = None

        if run_id:
            run = await db.get(AgentRun, run_id)

        if not run:
            run = AgentRun(
                portfolio_id=portfolio_id,
                run_type=run_type,
                session=session,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            db.add(run)
            await db.commit()
            await db.refresh(run)

        return str(run.id)


async def run_agent(
    portfolio_id: str,
    session: str = "manual",
    run_type: str = "manual",
    run_id: str | None = None,
) -> dict:
    resolved_run_id = await _load_or_create_run(portfolio_id, session, run_type, run_id)

    async with SessionLocal() as db:
        run = await db.get(AgentRun, resolved_run_id)
        portfolio = await db.get(Portfolio, portfolio_id)

        if not run or not portfolio:
            return {"status": "failed", "error": "Run or portfolio not found"}

        try:
            tickers = await get_portfolio_tickers(db, portfolio.id)
            holdings, _ = await build_holdings_view(db, portfolio.id)
            portfolio_out = await build_portfolio_out(db, portfolio)
            _ = build_context(
                portfolio=portfolio_out.model_dump(),
                holdings=[item.model_dump() for item in holdings],
                tickers=tickers,
                session=session,
            )

            if not tickers:
                run.summary = "No tickers configured for this portfolio."
                run.status = "done"
                run.trades_made = 0
                run.total_pl = portfolio_out.profit_loss
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return {"status": "done", "run_id": str(run.id)}

            trades_made = 0
            summary_lines: list[str] = []

            for ticker in tickers:
                try:
                    prediction = await _with_retries(predict_price_tool, ticker, horizon_days=3)
                    direction = await _with_retries(classify_direction_tool, ticker)
                    technical = await _with_retries(get_technical_signals_tool, ticker)
                    sentiment = await _with_retries(get_sentiment_score_tool, ticker)
                    status = await _with_retries(get_portfolio_status_tool, db, portfolio_id)
                    current_price = await _with_retries(get_current_price, ticker)
                except Exception as exc:
                    summary_lines.append(f"{ticker}: skipped due to tool error ({exc}).")
                    continue

                cash = float(status["current_cash"])
                matching_holding = next(
                    (item for item in status["holdings"] if item["ticker"] == ticker),
                    None,
                )
                owned_shares = float((matching_holding or {}).get("shares", 0.0))

                action = "HOLD"
                amount_usd: float | None = None
                sell_shares: float | None = None

                if (
                    direction.get("direction") == "UP"
                    and float(direction.get("probability", 0)) >= 0.55
                    and float(technical.get("rsi", 50)) < 72
                    and sentiment >= -0.1
                    and cash >= 50
                ):
                    action = "BUY"
                    amount_usd = max(50.0, min(cash * 0.08, 500.0))
                elif (
                    owned_shares > 0
                    and (
                        direction.get("direction") == "DOWN"
                        or sentiment < -0.25
                        or float(technical.get("rsi", 50)) > 78
                    )
                ):
                    action = "SELL"
                    sell_shares = round(max(owned_shares * 0.25, 0.000001), 6)

                reasoning = _build_reasoning(
                    ticker=ticker,
                    prediction=prediction,
                    direction=direction,
                    technical=technical,
                    sentiment=sentiment,
                    action=action,
                )

                await record_prediction(
                    db=db,
                    ticker=ticker,
                    model_type="lstm",
                    predicted_price=float(prediction.get("predicted_price", 0.0)),
                    actual_price=float(current_price),
                )

                if action in {"BUY", "SELL"}:
                    try:
                        await _with_retries(
                            execute_trade,
                            db=db,
                            portfolio_id=portfolio_id,
                            ticker=ticker,
                            action=action,
                            amount_usd=amount_usd,
                            shares=sell_shares,
                            llm_reasoning=reasoning,
                            tools_called={
                                "lstm_prediction": prediction,
                                "direction": direction,
                                "technical_signals": technical,
                                "sentiment_score": sentiment,
                            },
                        )
                    except Exception as exc:
                        summary_lines.append(f"{ticker}: trade execution failed ({exc}).")
                        continue
                    trades_made += 1

                summary_lines.append(reasoning)

            await snapshot_portfolio(db, portfolio.id)
            refreshed_portfolio = await build_portfolio_out(db, portfolio)

            run.status = "done"
            run.trades_made = trades_made
            run.total_pl = refreshed_portfolio.profit_loss
            run.summary = "\n".join(summary_lines[-10:])
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            return {
                "status": "done",
                "run_id": str(run.id),
                "trades_made": trades_made,
            }

        except Exception as exc:
            run.status = "failed"
            run.summary = f"Run failed: {exc}"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return {
                "status": "failed",
                "run_id": str(run.id),
                "error": str(exc),
            }
