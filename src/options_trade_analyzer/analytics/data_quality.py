"""Deterministic data-quality checks, so reliability flags never depend on the LLM's judgment.

Each function returns plain values the tools pass to the agent: how old a quote is, whether the
contract is liquid, how far the model price is from the market, and which model assumptions the
estimate leans on.
"""

import datetime as dt
from typing import Literal
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")

# Liquidity thresholds (per contract). Below "fair" an exit at a fair price gets hard.
SPREAD_PCT_GOOD, SPREAD_PCT_FAIR = 10.0, 25.0
OPEN_INTEREST_GOOD, OPEN_INTEREST_FAIR = 500, 100
VOLUME_GOOD, VOLUME_FAIR = 100, 10

MODEL_GAP_FLAG_PCT = 5.0  # model price this far from the mid-price is reported as a gap
FAR_OTM_PCT = 15.0
SHORT_DATED_DAYS = 3


def is_market_open(now: dt.datetime) -> bool:
    """Regular US equity session, Mon-Fri 9:30-16:00 New York time (exchange holidays not modeled)."""
    local = now.astimezone(NEW_YORK)
    return local.weekday() < 5 and dt.time(9, 30) <= local.time() < dt.time(16, 0)


def quote_freshness(last_trade: dt.datetime, now: dt.datetime) -> dict:
    """How old the contract's last trade is, and whether that matters right now."""
    age_hours = (now - last_trade).total_seconds() / 3600
    if is_market_open(now):
        status = "fresh" if age_hours <= 0.5 else "delayed"
    else:
        status = "market closed"
    return {
        "last_trade": last_trade.astimezone(NEW_YORK).strftime("%Y-%m-%d %H:%M ET"),
        "age_hours": round(age_hours, 1),
        "status": status,
    }


def liquidity_rating(spread_pct: float | None, volume: int, open_interest: int) -> dict:
    """Rate liquidity from fixed thresholds; the worst of the three measures sets the rating."""
    def grade(value, good, fair, higher_is_better=True) -> int:
        if value is None:
            return 2
        if not higher_is_better:
            value, good, fair = -value, -good, -fair
        return 0 if value >= good else 1 if value >= fair else 2

    grades = {
        "spread": grade(spread_pct, SPREAD_PCT_GOOD, SPREAD_PCT_FAIR, higher_is_better=False),
        "volume": grade(volume, VOLUME_GOOD, VOLUME_FAIR),
        "open interest": grade(open_interest, OPEN_INTEREST_GOOD, OPEN_INTEREST_FAIR),
    }
    worst = max(grades.values())
    issues = [name for name, g in grades.items() if g > 0]
    return {"rating": ["good", "fair", "poor"][worst], "issues": issues}


def model_vs_market(model_price: float, bid: float, ask: float) -> dict:
    """Compare the Black-Scholes price with the quoted market."""
    bid, ask, model_price = float(bid), float(ask), float(model_price)
    mid = (bid + ask) / 2 if bid > 0 and ask > 0 else None
    gap_pct = round((model_price - mid) / mid * 100, 1) if mid else None
    return {
        "model_price": round(model_price, 2),
        "market_mid": round(mid, 2) if mid else None,
        "model_minus_mid_pct": gap_pct,
        "model_within_bid_ask": bool(bid <= model_price <= ask) if mid else None,
        "gap_flag": bool(gap_pct is not None and abs(gap_pct) >= MODEL_GAP_FLAG_PCT),
    }


def model_assumption_flags(
    option_type: Literal["call", "put"],
    spot: float,
    strike: float,
    days_to_expiry: int,
    earnings_before_expiry: bool,
    ex_dividend_before_expiry: bool,
) -> list[str]:
    """Conditions under which Black-Scholes figures lean heavily on assumptions that may not hold."""
    flags = []
    if earnings_before_expiry:
        flags.append("earnings before expiration: volatility is unlikely to stay constant; "
                     "post-earnings prices are scenarios, not forecasts")
    if days_to_expiry <= SHORT_DATED_DAYS:
        flags.append("expires within days: Greeks change very quickly")
    otm_pct = (strike - spot) / spot * 100 if option_type == "call" else (spot - strike) / spot * 100
    if otm_pct >= FAR_OTM_PCT:
        flags.append(f"far out of the money ({otm_pct:.0f}%): model value is small and sensitive to volatility")
    if ex_dividend_before_expiry:
        flags.append("ex-dividend date before expiration: the model ignores dividends and early exercise")
    return flags
