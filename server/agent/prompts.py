from __future__ import annotations

SYSTEM_PROMPT = """
You are AlphaEngine's portfolio trading assistant.
Make conservative, explainable paper-trading decisions using model signals,
technical indicators, and recent news sentiment.
Always preserve risk controls and avoid over-allocation.
""".strip()


def build_context(
    portfolio: dict,
    holdings: list[dict],
    tickers: list[str],
    session: str,
) -> str:
    return (
        f"Session: {session}\n"
        f"Portfolio Name: {portfolio.get('name')}\n"
        f"Current Cash: {portfolio.get('current_cash')}\n"
        f"Total Value: {portfolio.get('total_value')}\n"
        f"Tickers: {', '.join(tickers)}\n"
        f"Current Holdings: {holdings}\n"
        "Goal: choose BUY/SELL/HOLD actions with concise reasoning and disciplined sizing."
    )
