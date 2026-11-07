"""Risk-adjusted measures: is an alternative better, or does it only have a smaller maximum loss?

Every measure is for one set of contracts held to its own expiration and is deterministic:
- expected profit and chance of profit under two price views: Black-Scholes (risk-neutral, the
  view the option prices themselves imply) and the stock's own past moves over the same horizon
  (every overlapping window in the history, no random sampling);
- the cost of crossing the bid-ask spread, which mid-quote figures leave out;
- the value change under several implied-volatility shifts;
- reward per dollar risked (maximum gain / maximum loss).
Neither price view is a forecast. Risk-neutral expected profit is about zero by construction; with
one shared volatility for legs whose implied volatilities differ (skew), what remains is mispricing,
not an edge, so comparisons use its chance of profit only. Past moves carry the drift of their period.
"""

import math
from statistics import NormalDist

import pandas as pd

from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.analytics import strategies

IV_SHIFTS_PCT = (-40, -20, 20)
GRID_POINTS = 2000  # quantiles of the risk-neutral price distribution
TRADING_DAYS_PER_YEAR = 252


def _outcomes(position: alt.Position, prices: list[float], discount: float) -> dict:
    """Average profit in today's dollars (expiry value discounted, minus the mid-quote cost) and the
    share of prices where the position ends with a profit at expiration."""
    legs = list(position.legs)
    cost = strategies.net_cost(legs)
    payoffs = [strategies.payoff(legs, p) for p in prices]
    expected = sum(discount * (p + cost) - cost for p in payoffs) / len(payoffs)
    return {"expected_pnl": round(expected, 2),
            "chance_of_profit_pct": round(sum(p > 0 for p in payoffs) / len(payoffs) * 100, 1)}


def risk_neutral(position: alt.Position, market: alt.Market) -> dict:
    """Expected profit and chance of profit if the stock follows the Black-Scholes distribution
    (drift = risk-free rate, volatility = the legs' average implied volatility)."""
    years = alt.years_to_expiry(position.expiration, market.today)
    sigma = sum(position.ivs) / len(position.ivs)
    drift = (market.rate - sigma ** 2 / 2) * years
    normal = NormalDist()
    prices = [market.spot * math.exp(drift + sigma * math.sqrt(years) * normal.inv_cdf((i + 0.5) / GRID_POINTS))
              for i in range(GRID_POINTS)]
    return _outcomes(position, prices, math.exp(-market.rate * years))


def historical(position: alt.Position, market: alt.Market, closes: pd.Series) -> dict:
    """Expected profit and chance of profit if the stock repeats one of its past moves over the same
    number of trading days, applied to today's price (every overlapping window in `closes`)."""
    calendar_days = (pd.Timestamp(position.expiration).date() - market.today).days
    days = max(1, round(calendar_days * TRADING_DAYS_PER_YEAR / 365))
    values = closes.dropna().to_numpy()
    if len(values) <= days:
        return {"error": f"need more than {days} closes, have {len(values)}"}
    ratios = values[days:] / values[:-days]
    years = alt.years_to_expiry(position.expiration, market.today)
    result = _outcomes(position, [market.spot * float(r) for r in ratios], math.exp(-market.rate * years))
    return result | {"windows": len(ratios), "trading_days": days}


def spread_cost(position: alt.Position, market: alt.Market) -> dict:
    """Dollars lost to the bid-ask spread versus the mid-quote: once to open, twice to open and close."""
    one_way = alt.open_cost(position, market)
    return {"open": one_way, "round_trip": round(2 * one_way, 2)}


def measure(position: alt.Position, market: alt.Market, closes: pd.Series) -> dict:
    """All risk-adjusted measures for one position."""
    legs = list(position.legs)
    loss, gain = strategies.max_loss(legs), strategies.max_gain(legs)
    return {
        "strategy": position.name,
        "expiration": position.expiration,
        "max_loss": loss,
        "max_gain": "unlimited" if gain is None else gain,
        "reward_to_risk": None if gain is None or not loss else round(gain / loss, 2),
        "risk_neutral": risk_neutral(position, market),
        "historical": historical(position, market, closes),
        "spread_cost": spread_cost(position, market),
        "iv_change": {f"{pct:+d}%": alt.iv_change(position, market, pct) for pct in IV_SHIFTS_PCT},
    }
