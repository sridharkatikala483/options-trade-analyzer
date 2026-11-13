"""Input risk flags (Checkpoint 6 "shown with a warning"): computed by code from the contract lookup."""

import pytest

from options_trade_analyzer.analytics import input_risk

SAFE = {"option_type": "call", "stock_price": 100.0, "breakeven": 103.0, "days_to_expiry": 35,
        "implied_volatility_pct": 30.0,
        "data_quality": {"liquidity": {"rating": "good", "issues": []},
                         "quote": {"status": "open", "last_trade": "2026-11-06 15:59 ET"}}}


def ids(contract):
    return [f["id"] for f in input_risk.flags(contract)]


def test_a_liquid_open_market_contract_with_time_left_has_no_flags():
    assert ids(SAFE) == []


@pytest.mark.parametrize("change, expected", [
    ({"days_to_expiry": 2}, "short_expiry"),
    ({"data_quality": {"liquidity": {"rating": "poor", "issues": ["spread"]}, "quote": {"status": "open"}}},
     "poor_liquidity"),
    ({"data_quality": {"liquidity": {"rating": "good"}, "quote": {"status": "market closed",
                                                                  "last_trade": "2026-11-06 15:59 ET"}}},
     "closed_market"),
    ({"breakeven": 130.0}, "low_chance"),
])
def test_each_risk_is_flagged(change, expected):
    assert expected in ids(SAFE | change)


def test_three_days_left_is_not_short():
    assert "short_expiry" not in ids(SAFE | {"days_to_expiry": 3})


def test_chance_beyond_breakeven_behaves():
    near = input_risk.chance_beyond_breakeven("call", 100, 101, 35, 30)
    far = input_risk.chance_beyond_breakeven("call", 100, 130, 35, 30)
    put_far = input_risk.chance_beyond_breakeven("put", 100, 70, 35, 30)
    assert 0.3 < near < 0.5 and far < 0.05 and put_far < 0.05


def test_the_low_chance_message_quotes_the_rounded_number():
    flag = next(f for f in input_risk.flags(SAFE | {"breakeven": 130.0}) if f["id"] == "low_chance")
    assert f"{flag['chance_beyond_breakeven_pct']}%" in flag["message"] and "not a forecast" in flag["message"]


def test_missing_fields_do_not_raise():
    assert input_risk.flags({}) == []
