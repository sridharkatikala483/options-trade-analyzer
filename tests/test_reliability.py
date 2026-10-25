"""Reliability checks added after Checkpoint 2 feedback.

1. Independent verification: a separate Black-Scholes written from the formulas (math.erf only)
   must match the vollib-based options_math across a grid of scenarios.
2. Data-quality checks: freshness, liquidity rating, model-vs-market gap, assumption flags.
3. Strategy comparison: the AAPL 350/360 bull call spread example from the feedback response.
"""

import datetime as dt
import math

import pytest

from options_trade_analyzer.analytics import data_quality as dq
from options_trade_analyzer.analytics import options_math
from options_trade_analyzer.analytics.strategies import Leg, breakevens, max_gain, max_loss, net_cost, payoff


# ---------- 1. Independent Black-Scholes ----------

def _cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _pdf(x: float) -> float:
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def independent_bs(kind: str, s: float, k: float, t: float, r: float, v: float) -> dict:
    d1 = (math.log(s / k) + (r + v * v / 2) * t) / (v * math.sqrt(t))
    d2 = d1 - v * math.sqrt(t)
    disc = math.exp(-r * t)
    if kind == "call":
        price, delta = s * _cdf(d1) - k * disc * _cdf(d2), _cdf(d1)
        theta = (-s * _pdf(d1) * v / (2 * math.sqrt(t)) - r * k * disc * _cdf(d2)) / 365
    else:
        price, delta = k * disc * _cdf(-d2) - s * _cdf(-d1), _cdf(d1) - 1
        theta = (-s * _pdf(d1) * v / (2 * math.sqrt(t)) + r * k * disc * _cdf(-d2)) / 365
    return {
        "price": price,
        "delta": delta,
        "gamma": _pdf(d1) / (s * v * math.sqrt(t)),
        "theta": theta,
        "vega": s * _pdf(d1) * math.sqrt(t) / 100,
    }


SCENARIOS = [
    (kind, s, k, t, v)
    for kind in ("call", "put")
    for s, k in [(100, 100), (100, 85), (100, 120), (347.73, 350)]
    for t in (3 / 365, 30 / 365, 1.0)
    for v in (0.15, 0.35, 0.8)
]


@pytest.mark.parametrize("kind,s,k,t,v", SCENARIOS)
def test_options_math_matches_independent_black_scholes(kind, s, k, t, v):
    r = 0.04
    expected = independent_bs(kind, s, k, t, r, v)
    assert options_math.bs_price(kind, s, k, t, r, v) == pytest.approx(expected["price"], abs=1e-4)
    greeks = options_math.greeks(kind, s, k, t, r, v)
    for name in ("delta", "gamma", "theta", "vega"):
        assert greeks[name] == pytest.approx(expected[name], abs=1e-4), name


# ---------- 2. Data-quality checks ----------

ET = dq.NEW_YORK


def test_market_closed_on_weekend():
    saturday = dt.datetime(2026, 10, 24, 12, 0, tzinfo=ET)
    friday_close = dt.datetime(2026, 10, 23, 15, 59, tzinfo=ET)
    result = dq.quote_freshness(friday_close, saturday)
    assert result["status"] == "market closed"
    assert result["age_hours"] == pytest.approx(20.0, abs=0.1)


def test_delayed_quote_during_session():
    now = dt.datetime(2026, 10, 26, 14, 0, tzinfo=ET)  # Monday
    assert dq.quote_freshness(now - dt.timedelta(minutes=10), now)["status"] == "fresh"
    assert dq.quote_freshness(now - dt.timedelta(hours=2), now)["status"] == "delayed"


def test_liquidity_rating_uses_worst_measure():
    assert dq.liquidity_rating(4.0, 791, 5461) == {"rating": "good", "issues": []}  # demo contract
    assert dq.liquidity_rating(17.0, 791, 5461)["rating"] == "fair"
    poor = dq.liquidity_rating(4.0, 3, 40)
    assert poor["rating"] == "poor" and set(poor["issues"]) == {"volume", "open interest"}


def test_model_vs_market_gap_from_demo_contract():
    result = dq.model_vs_market(8.06, 7.35, 7.65)
    assert result["market_mid"] == 7.5
    assert result["model_minus_mid_pct"] == pytest.approx(7.5, abs=0.1)
    assert result["model_within_bid_ask"] is False and result["gap_flag"] is True


def test_assumption_flags():
    flags = dq.model_assumption_flags("call", 347.73, 350, 13, earnings_before_expiry=True,
                                      ex_dividend_before_expiry=False)
    assert len(flags) == 1 and flags[0].startswith("earnings before expiration")
    far = dq.model_assumption_flags("put", 100, 80, 2, False, True)
    assert len(far) == 3  # short-dated, far out of the money, ex-dividend


# ---------- 3. Strategy comparison ----------

LONG_CALL = [Leg("call", 350, 7.50)]
BULL_SPREAD = [Leg("call", 350, 7.50), Leg("call", 360, 3.45, -1)]


def test_long_call_profile():
    assert net_cost(LONG_CALL) == 750
    assert max_loss(LONG_CALL) == 750
    assert max_gain(LONG_CALL) is None  # unlimited
    assert breakevens(LONG_CALL) == [357.5]


def test_bull_call_spread_profile():
    assert net_cost(BULL_SPREAD) == pytest.approx(405)
    assert max_loss(BULL_SPREAD) == 405
    assert max_gain(BULL_SPREAD) == 595
    assert breakevens(BULL_SPREAD) == [354.05]


@pytest.mark.parametrize("price,long_call,spread", [
    (345, -750, -405), (355, -250, 95), (360, 250, 595), (370, 1250, 595),
])
def test_payoff_table_same_assumptions(price, long_call, spread):
    assert payoff(LONG_CALL, price) == pytest.approx(long_call)
    assert payoff(BULL_SPREAD, price) == pytest.approx(spread)
