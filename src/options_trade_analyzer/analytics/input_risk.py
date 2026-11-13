"""Input risk flags: dangers in the proposed contract itself, found by code before any agent runs.

They do not block the analysis (the report is how a beginner learns why the contract is risky); they are
shown above the report and passed to the Writer as evidence. Checkpoint 6 calls this outcome "shown with a
warning". The chance is risk-neutral (Black-Scholes): an estimate of how often the stock ends beyond the
breakeven, not a forecast.
"""

import math

from options_trade_analyzer import config

SHORT_DAYS = 2        # this few days left: time decay and any move dominate
LOW_CHANCE = 0.15     # below this chance of finishing beyond breakeven, the same floor the alternative search uses


def chance_beyond_breakeven(option_type: str, stock_price: float, breakeven: float, days: int, iv_pct: float,
                            rate: float = config.RISK_FREE_RATE) -> float | None:
    """Risk-neutral probability that the stock finishes past the breakeven at expiry."""
    years, iv = max(days, 0.5) / 365, iv_pct / 100
    if stock_price <= 0 or breakeven <= 0 or iv <= 0:
        return None
    d2 = (math.log(stock_price / breakeven) + (rate - iv * iv / 2) * years) / (iv * math.sqrt(years))
    above = 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
    return above if option_type == "call" else 1 - above


def flags(contract: dict) -> list[dict]:
    """Warnings for one get_option_contract result: id, plain-language message, and the numbers behind it."""
    out = []
    days = contract.get("days_to_expiry")
    if days is not None and days <= SHORT_DAYS:
        out.append({"id": "short_expiry", "days_to_expiry": days,
                    "message": f"Only {days} day{'s' if days != 1 else ''} to expiry: time decay is fastest now "
                               "and the option can lose most of its value in a day."})
    quality = contract.get("data_quality", {})
    liquidity = quality.get("liquidity", {})
    if liquidity.get("rating") == "poor":
        issues = ", ".join(liquidity.get("issues", [])) or "spread, volume or open interest"
        out.append({"id": "poor_liquidity", "issues": liquidity.get("issues", []),
                    "message": f"Liquidity is rated poor ({issues}): buying and selling may cost a wide spread."})
    quote = quality.get("quote", {})
    if quote.get("status") == "market closed":
        out.append({"id": "closed_market", "last_trade": quote.get("last_trade"),
                    "message": f"Prices are from the last trade ({quote.get('last_trade', 'time unknown')}), "
                               "not live: they may differ when the market opens."})
    chance = None if days is None else chance_beyond_breakeven(
        contract.get("option_type", "call"), contract.get("stock_price", 0), contract.get("breakeven", 0),
        days, contract.get("implied_volatility_pct", 0))
    if chance is not None and chance < LOW_CHANCE:
        pct = round(chance * 100, 1)
        out.append({"id": "low_chance", "chance_beyond_breakeven_pct": pct,
                    "message": f"The Black-Scholes model gives about a {pct}% chance that the stock finishes "
                               "beyond the breakeven by expiry (an estimate, not a forecast)."})
    return out
