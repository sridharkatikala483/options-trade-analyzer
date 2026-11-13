"""Missing market data (Week 5 feedback): gaps are reported, never crash a tool, and hold the run for review."""

import json

import pandas as pd
import pytest

from options_trade_analyzer import review
from options_trade_analyzer.agents import tools
from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.analytics import input_risk

CHAIN = pd.DataFrame([{"strike": 100.0, "lastPrice": 2.0, "bid": 1.9, "ask": 2.1, "impliedVolatility": 0.3,
                       "volume": 500, "openInterest": 2000,
                       "lastTradeDate": pd.Timestamp("2026-11-13 15:00", tz="UTC")}])


class Provider:
    def __init__(self, chain=CHAIN, fail=()):
        self.chain, self.fail = chain, set(fail)

    def _maybe_fail(self, name):
        if name in self.fail:
            raise KeyError(f"not in snapshot: {name}")

    def get_quote(self, ticker):
        return 100.0

    def get_expirations(self, ticker):
        return ["2026-12-18", "2027-01-15"]

    def get_option_chain(self, ticker, expiration):
        self._maybe_fail(f"chain {expiration}")
        return {"calls": self.chain.copy(), "puts": self.chain.copy()}

    def get_next_earnings_date(self, ticker):
        return None

    def get_next_ex_dividend_date(self, ticker):
        return None

    def get_price_history(self, ticker, period="6mo"):
        self._maybe_fail("history")
        raise AssertionError("not used")


@pytest.fixture
def use(monkeypatch):
    def install(provider):
        monkeypatch.setattr(tools, "provider", provider)
        return provider
    return install


def contract():
    return json.loads(tools.get_option_contract.invoke(
        {"ticker": "T", "option_type": "call", "strike": 100.0, "expiration": "2026-12-18"}))


def test_a_blank_implied_volatility_is_reported_not_passed_on_as_nan(use):
    use(Provider(CHAIN.assign(impliedVolatility=float("nan"))))
    data = contract()
    assert data["implied_volatility_pct"] is None and "implied volatility" in data["data_quality"]["missing"][0]
    assert data["data_quality"]["model_vs_market"]["status"].startswith("unavailable")
    assert [f["id"] for f in input_risk.flags(data)][0] == "missing_data"


def test_no_bid_or_ask_is_reported_as_missing(use):
    use(Provider(CHAIN.assign(bid=0.0, ask=0.0)))
    data = contract()
    assert data["premium"] == 2.0 and data["implied_volatility_pct"] is None
    assert data["data_quality"]["missing"][0].startswith("bid/ask quote")


def test_a_failed_source_becomes_an_error_the_agent_can_report(use):
    use(Provider(fail={"history"}))
    data = json.loads(tools.get_price_trend.invoke({"ticker": "T"}))
    assert data["error"].startswith("data unavailable") and "do not guess" in data["note"]


def test_the_search_skips_an_expiration_whose_chain_did_not_load():
    market = alt.Market(Provider(fail={"chain 2027-01-15"}), "T", 0.04)
    assert market.quotes("2027-01-15", "call") == {} and market.quotes("2026-12-18", "call")


def test_missing_data_and_failed_sources_hold_the_run_for_review():
    flag = {"id": "missing_data", "missing": ["implied volatility: ..."], "message": "Data missing"}
    assert review.decide([], {}, {}, [flag])[0] == "needs_review"
    failed = [{"step": "Observation", "tool": "get_price_trend", "text": json.dumps({"error": "data unavailable (KeyError)"})}]
    assert review.failed_sources(failed) == ["get_price_trend"]
    recovered = failed + [{"step": "Observation", "tool": "get_price_trend", "text": json.dumps({"trend": "up"})}]
    assert review.failed_sources(recovered) == []
    assert review.decide([], {}, {}, [], failed_sources=["get_price_trend"])[0] == "needs_review"
