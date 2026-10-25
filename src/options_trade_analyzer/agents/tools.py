"""LangChain tools for the agents. Each wraps tested data/math code and returns compact JSON text.

Tools validate their inputs and return {"error": ...} instead of raising, so the agent can observe
the problem and correct its next action (the ReAct error-recovery path).
"""

import datetime as dt
import json

from langchain_core.tools import BaseTool, tool

from options_trade_analyzer import config
from options_trade_analyzer.analytics import options_math
from options_trade_analyzer.data import get_provider
from options_trade_analyzer.retrieval.knowledge import search_knowledge
from options_trade_analyzer.retrieval.news import search_news

provider = get_provider(config.DATA_PROVIDER)


def _json(data: dict) -> str:
    return json.dumps(data, default=str)


def _years_to_expiry(expiration: str) -> float:
    # Count to the expiration day's close, so a contract expiring today still has a little time left.
    return max((dt.date.fromisoformat(expiration) - dt.date.today()).days + 0.5, 0.5) / 365


@tool
def get_option_contract(ticker: str, option_type: str, strike: float, expiration: str) -> str:
    """Look up one option contract: stock price, premium, bid/ask spread, implied volatility, volume,
    open interest, days to expiry and breakeven. option_type is "call" or "put"; expiration is YYYY-MM-DD."""
    if option_type not in ("call", "put"):
        return _json({"error": "option_type must be 'call' or 'put'"})
    try:
        if dt.date.fromisoformat(expiration) < dt.date.today():
            return _json({"error": f"expiration {expiration} is in the past"})
    except ValueError:
        return _json({"error": "expiration must be YYYY-MM-DD"})
    if expiration not in provider.get_expirations(ticker):
        return _json({"error": f"no {ticker} options expire on {expiration}",
                      "available": provider.get_expirations(ticker)[:8]})

    chain = provider.get_option_chain(ticker, expiration)[f"{option_type}s"]
    rows = chain[chain["strike"] == strike]
    if rows.empty:
        nearby = sorted(chain["strike"], key=lambda s: abs(s - strike))[:5]
        return _json({"error": f"strike {strike} not listed", "nearest_strikes": sorted(nearby)})

    row = rows.iloc[0]
    bid, ask = float(row["bid"]), float(row["ask"])
    premium = (bid + ask) / 2 if bid > 0 and ask > 0 else float(row["lastPrice"])
    return _json({
        "ticker": ticker,
        "option_type": option_type,
        "strike": strike,
        "expiration": expiration,
        "stock_price": round(provider.get_quote(ticker), 2),
        "premium": round(premium, 2),
        "bid": bid,
        "ask": ask,
        "spread_pct_of_premium": round((ask - bid) / premium * 100, 1) if premium else None,
        "implied_volatility_pct": round(float(row["impliedVolatility"]) * 100, 1),
        "volume": int(row["volume"]) if row["volume"] == row["volume"] else 0,
        "open_interest": int(row["openInterest"]) if row["openInterest"] == row["openInterest"] else 0,
        "days_to_expiry": (dt.date.fromisoformat(expiration) - dt.date.today()).days,
        "breakeven": round(options_math.breakeven(option_type, strike, premium), 2),
        "max_loss_per_contract": round(premium * 100, 2),
    })


@tool
def compute_greeks(option_type: str, stock_price: float, strike: float, expiration: str,
                   implied_volatility_pct: float, iv_change_pct: float = 0) -> str:
    """Calculate Black-Scholes Greeks (delta, gamma, theta per day, vega per 1 IV point) and the model
    price. Pass implied_volatility_pct as a percentage, e.g. 27.5. To test a volatility drop, call it
    again with iv_change_pct=-40 (implied volatility 40% lower than now)."""
    if not 1 <= implied_volatility_pct <= 500:
        return _json({"error": "implied_volatility_pct looks invalid; pass a percentage such as 27.5"})
    if not -90 <= iv_change_pct <= 200:
        return _json({"error": "iv_change_pct must be between -90 and 200"})
    implied_volatility_pct = round(implied_volatility_pct * (1 + iv_change_pct / 100), 2)
    years, iv = _years_to_expiry(expiration), implied_volatility_pct / 100
    greeks = options_math.greeks(option_type, stock_price, strike, years, config.RISK_FREE_RATE, iv)
    price = options_math.bs_price(option_type, stock_price, strike, years, config.RISK_FREE_RATE, iv)
    return _json({
        "implied_volatility_pct": implied_volatility_pct,
        "model_price": round(price, 2),
        **{name: round(value, 4) for name, value in greeks.items()},
        "theta_per_contract_per_day": round(greeks["theta"] * 100, 2),
        "note": "Black-Scholes approximates American-style options",
    })


@tool
def get_earnings_date(ticker: str) -> str:
    """Next scheduled earnings date for the ticker, if known."""
    date = provider.get_next_earnings_date(ticker)
    return _json({"ticker": ticker, "next_earnings_date": date or "unknown"})


@tool
def search_options_knowledge(query: str) -> str:
    """Search the options knowledge base for explanations of concepts relevant to this trade
    (e.g. "volatility crush after earnings", "time decay near expiration", "wide bid-ask spread").
    Returns passages with source ids to cite as [KB: source]."""
    hits = search_knowledge(query)
    if not hits:
        return _json({"results": [], "note": "No sufficiently relevant passage. Do not invent one."})
    return _json({"results": [
        {"source": h.metadata["source"], "relevance": round(h.score, 2), "text": h.text} for h in hits
    ]})


@tool
def search_recent_news(ticker: str, query: str) -> str:
    """Search headlines from the last 14 days about the ticker, de-duplicated with MMR so each result
    is a distinct story. Use a query describing what could move the stock before expiration."""
    hits = search_news(ticker, query)
    if not hits:
        return _json({"results": [], "note": "No recent headlines available."})
    return _json({"results": [
        {"headline": h.text, "source": h.metadata["source"], "date": h.metadata["date"]} for h in hits
    ]})


CORE_TOOLS: list[BaseTool] = [get_option_contract, compute_greeks, get_earnings_date]
RETRIEVAL_TOOLS: list[BaseTool] = [search_options_knowledge, search_recent_news]
