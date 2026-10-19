import pytest

from options_trade_analyzer.analytics.options_math import breakeven, bs_price, greeks, payoff_at_expiry

# Textbook case: S=100, K=100, T=1 year, r=5%, sigma=20%
S, K, T, R, IV = 100.0, 100.0, 1.0, 0.05, 0.20


def test_call_price_matches_textbook():
    assert bs_price("call", S, K, T, R, IV) == pytest.approx(10.4506, abs=1e-3)


def test_put_price_matches_textbook():
    assert bs_price("put", S, K, T, R, IV) == pytest.approx(5.5735, abs=1e-3)


def test_call_delta_matches_textbook():
    assert greeks("call", S, K, T, R, IV)["delta"] == pytest.approx(0.6368, abs=1e-3)


def test_breakeven():
    assert breakeven("call", 100, 5) == 105
    assert breakeven("put", 100, 5) == 95


def test_payoff_at_expiry():
    assert payoff_at_expiry("call", 100, 5, 110) == 500
    assert payoff_at_expiry("call", 100, 5, 90) == -500
    assert payoff_at_expiry("put", 100, 5, 90) == 500
