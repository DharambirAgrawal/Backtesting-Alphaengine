from __future__ import annotations

import asyncio
import json
import re
from statistics import median
from datetime import datetime, timezone

from sqlalchemy import select

from agent.tools import (
    classify_direction_tool,
    execute_trade,
    get_portfolio_status_tool,
    get_sentiment_score_tool,
    get_technical_signals_tool,
    predict_price_tool,
)
from api.utils import build_holdings_view, build_portfolio_out, get_portfolio_tickers, snapshot_portfolio
from core.config import settings
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


def _rule_decision(
    *,
    cash: float,
    owned_shares: float,
    direction: dict,
    technical: dict,
    sentiment: float,
) -> dict:
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

    return {
        "action": action,
        "amount_usd": amount_usd,
        "sell_shares": sell_shares,
        "preferred_minutes": None,
        "source": "rules",
    }


def _extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


async def _llm_hybrid_decision(
    *,
    ticker: str,
    cash: float,
    owned_shares: float,
    prediction: dict,
    direction: dict,
    technical: dict,
    sentiment: float,
    baseline: dict,
) -> dict | None:
    mode = settings.AGENT_DECISION_MODE.lower().strip()
    if mode == "rules" or not settings.GEMINI_API_KEY:
        return None

    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        return None

    prompt = f"""
You are a risk-aware paper-trading assistant.
Decide one action for a single ticker using both quant signals and baseline rule suggestion.
Return STRICT JSON only with keys:
action (BUY|SELL|HOLD), amount_usd (number|null), sell_fraction (number|null), preferred_minutes (int|null), rationale (string).

Ticker: {ticker}
Cash available: {cash}
Owned shares: {owned_shares}
Prediction: {json.dumps(prediction)}
Direction: {json.dumps(direction)}
Technical: {json.dumps(technical)}
Sentiment: {sentiment}
Baseline rule decision: {json.dumps(baseline)}

Hard limits:
- BUY only if cash >= 50.
- SELL only if owned_shares > 0.
- amount_usd must be between 50 and 1000 when BUY.
- sell_fraction between 0.1 and 1.0 when SELL.
- preferred_minutes between 20 and 240.
""".strip()

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        # 30-second hard timeout — prevents stalling the whole agent loop on slow/unavailable LLM
        response = await asyncio.wait_for(
            asyncio.to_thread(model.generate_content, prompt),
            timeout=30.0,
        )
        text = getattr(response, "text", "") or ""
        payload = _extract_json_object(text)
        if not isinstance(payload, dict):
            return None
        action = str(payload.get("action", "")).upper().strip()
        if action not in {"BUY", "SELL", "HOLD"}:
            return None
        amount_raw = payload.get("amount_usd")
        sell_fraction_raw = payload.get("sell_fraction")
        minutes_raw = payload.get("preferred_minutes")
        rationale = str(payload.get("rationale", "")).strip()

        amount_usd = float(amount_raw) if isinstance(amount_raw, (int, float)) else None
        sell_fraction = (
            float(sell_fraction_raw) if isinstance(sell_fraction_raw, (int, float)) else None
        )
        preferred_minutes = (
            int(minutes_raw) if isinstance(minutes_raw, (int, float)) else None
        )

        return {
            "action": action,
            "amount_usd": amount_usd,
            "sell_fraction": sell_fraction,
            "preferred_minutes": preferred_minutes,
            "source": "llm",
            "rationale": rationale,
        }
    except Exception:
        return None


def _merge_hybrid_decision(
    *,
    baseline: dict,
    llm: dict | None,
    cash: float,
    owned_shares: float,
) -> dict:
    final = dict(baseline)
    if not llm:
        return final

    action = str(llm.get("action", baseline["action"])).upper().strip()
    if action not in {"BUY", "SELL", "HOLD"}:
        action = baseline["action"]

    amount_usd: float | None = None
    sell_shares: float | None = None

    if action == "BUY":
        if cash < 50:
            action = "HOLD"
        else:
            llm_amount = llm.get("amount_usd")
            baseline_amount = baseline.get("amount_usd")
            amount_val = (
                float(llm_amount)
                if isinstance(llm_amount, (int, float))
                else float(baseline_amount or 50.0)
            )
            amount_usd = max(50.0, min(amount_val, min(cash, 1000.0)))

    elif action == "SELL":
        if owned_shares <= 0:
            action = "HOLD"
        else:
            sell_fraction = llm.get("sell_fraction")
            frac = (
                float(sell_fraction)
                if isinstance(sell_fraction, (int, float))
                else 0.25
            )
            frac = max(0.1, min(frac, 1.0))
            sell_shares = round(max(owned_shares * frac, 0.000001), 6)

    preferred_minutes = llm.get("preferred_minutes")
    final.update(
        {
            "action": action,
            "amount_usd": amount_usd,
            "sell_shares": sell_shares,
            "preferred_minutes": (
                max(20, min(int(preferred_minutes), 240))
                if isinstance(preferred_minutes, (int, float))
                else baseline.get("preferred_minutes")
            ),
            "source": llm.get("source", "rules"),
            "llm_rationale": llm.get("rationale"),
        }
    )
    return final


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
            confidence_values: list[float] = []
            bearish_signals = 0
            bullish_signals = 0
            tool_errors = 0
            preferred_minutes_votes: list[int] = []

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
                    tool_errors += 1
                    continue

                cash = float(status["current_cash"])
                matching_holding = next(
                    (item for item in status["holdings"] if item["ticker"] == ticker),
                    None,
                )
                owned_shares = float((matching_holding or {}).get("shares", 0.0))

                baseline = _rule_decision(
                    cash=cash,
                    owned_shares=owned_shares,
                    direction=direction,
                    technical=technical,
                    sentiment=sentiment,
                )
                llm_pick = await _llm_hybrid_decision(
                    ticker=ticker,
                    cash=cash,
                    owned_shares=owned_shares,
                    prediction=prediction,
                    direction=direction,
                    technical=technical,
                    sentiment=sentiment,
                    baseline=baseline,
                )
                decision = _merge_hybrid_decision(
                    baseline=baseline,
                    llm=llm_pick,
                    cash=cash,
                    owned_shares=owned_shares,
                )
                action = decision["action"]
                amount_usd = decision.get("amount_usd")
                sell_shares = decision.get("sell_shares")
                pref = decision.get("preferred_minutes")
                if isinstance(pref, int):
                    preferred_minutes_votes.append(pref)

                conf = float(prediction.get("confidence", 0.5))
                confidence_values.append(conf)
                if direction.get("direction") == "UP":
                    bullish_signals += 1
                elif direction.get("direction") == "DOWN":
                    bearish_signals += 1

                reasoning = _build_reasoning(
                    ticker=ticker,
                    prediction=prediction,
                    direction=direction,
                    technical=technical,
                    sentiment=sentiment,
                    action=action,
                )
                if decision.get("source") == "llm":
                    llm_rationale = str(decision.get("llm_rationale") or "").strip()
                    if llm_rationale:
                        reasoning = f"{reasoning} LLM rationale: {llm_rationale}"

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
                                "decision_source": decision.get("source", "rules"),
                                "decision_mode": settings.AGENT_DECISION_MODE,
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

            if portfolio.is_active:
                from scheduler.jobs import compute_next_market_run, schedule_portfolio_run

                avg_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5
                minutes = 180
                if trades_made > 0:
                    minutes = 60
                if avg_conf >= 0.72 or bullish_signals >= max(2, len(tickers) // 2):
                    minutes = min(minutes, 45)
                if bearish_signals >= max(2, len(tickers) // 2):
                    minutes = min(minutes, 60)
                if tool_errors > 0:
                    minutes = max(minutes, 120)
                if preferred_minutes_votes:
                    minutes = int((minutes + median(preferred_minutes_votes)) / 2)
                    minutes = max(20, min(minutes, 240))

                next_run_at = compute_next_market_run(preferred_minutes=minutes)
                schedule_portfolio_run(
                    portfolio_id=str(portfolio.id),
                    run_at_utc=next_run_at,
                    session="adaptive",
                )

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
