"""Risk-adjusted measures on the synthetic Black-Scholes chain from test_tot (offline, deterministic)."""

import math

import pandas as pd
import pytest
from test_tot import EXPIRATIONS, RATE, SPOT, TODAY, FakeProvider

from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.analytics import risk_metrics, strategies


@pytest.fixture
def market():
    return alt.Market(FakeProvider(), "TEST", RATE, today=TODAY)


def test_risk_neutral_expected_profit_is_about_zero_at_model_prices(market):
    # the fake chain's mid-quotes are Black-Scholes prices, so the fair-game average is about $0
    call = alt.original("call", 102.0, EXPIRATIONS[3], market)
    spread = alt.build("bull call spread", (102.0, 107.0), EXPIRATIONS[3], market)
    for position in (call, spread):
        result = risk_metrics.risk_neutral(position, market)
        assert abs(result["expected_pnl"]) < 0.01 * strategies.max_loss(list(position.legs)) + 0.5
        assert 0 < result["chance_of_profit_pct"] < 50


def test_historical_uses_every_window_of_the_horizon(market):
    call = alt.original("call", 102.0, EXPIRATIONS[0], market)
    flat = pd.Series([SPOT] * 100)
    result = risk_metrics.historical(call, market, flat)
    days = round((pd.Timestamp(EXPIRATIONS[0]).date() - TODAY).days * 252 / 365)
    assert (result["trading_days"], result["windows"]) == (days, 100 - days)
    # a flat stock leaves the 102 call worthless: lose the whole cost, no chance of profit
    assert result["chance_of_profit_pct"] == 0
    assert result["expected_pnl"] == pytest.approx(-strategies.net_cost(list(call.legs)), abs=0.01)
    assert "error" in risk_metrics.historical(call, market, pd.Series([SPOT] * 3))


def test_rising_history_favours_the_call(market):
    call = alt.original("call", 102.0, EXPIRATIONS[0], market)
    rising = pd.Series([SPOT * math.exp(0.01 * i) for i in range(200)])  # +1% every trading day
    result = risk_metrics.historical(call, market, rising)
    assert result["chance_of_profit_pct"] == 100 and result["expected_pnl"] > 0


def test_spread_cost_counts_half_the_spread_per_leg(market):
    spread = alt.build("bull call spread", (102.0, 107.0), EXPIRATIONS[0], market)
    quotes = market.quotes(EXPIRATIONS[0], "call")
    expected = sum((quotes[k].ask - quotes[k].bid) / 2 * 100 for k in (102.0, 107.0))
    cost = risk_metrics.spread_cost(spread, market)
    assert cost["open"] == pytest.approx(expected, abs=0.01)
    assert cost["round_trip"] == pytest.approx(2 * cost["open"], abs=0.01)


def test_measure_shows_the_trade_offs(market):
    closes = pd.Series([SPOT] * 300)
    call = risk_metrics.measure(alt.original("call", 102.0, EXPIRATIONS[0], market), market, closes)
    spread = risk_metrics.measure(alt.build("bull call spread", (102.0, 107.0), EXPIRATIONS[0], market),
                                  market, closes)
    assert call["max_gain"] == "unlimited" and call["reward_to_risk"] is None
    assert spread["reward_to_risk"] == pytest.approx(spread["max_gain"] / spread["max_loss"], abs=0.01)
    # the short leg offsets part of the volatility exposure, in both directions
    assert call["iv_change"]["-40%"] < spread["iv_change"]["-40%"] < 0
    assert call["iv_change"]["+20%"] > spread["iv_change"]["+20%"] > 0
    # two legs cross two bid-ask spreads
    assert spread["spread_cost"]["open"] > call["spread_cost"]["open"]
