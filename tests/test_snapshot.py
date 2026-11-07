"""Snapshot record and replay, offline: a fake live provider is recorded, saved, and replayed later."""

import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from options_trade_analyzer import clock, config
from options_trade_analyzer.agents import tools
from options_trade_analyzer.data import get_provider, news
from options_trade_analyzer.data.news import Headline
from options_trade_analyzer.data.snapshot import RecordingProvider, SnapshotProvider

RECORDED = dt.datetime(2026, 11, 6, 20, 0, tzinfo=dt.timezone.utc)
FETCH_HEADLINES = news.fetch_headlines  # the real function; the recording fixture replaces it with a fake feed
EXPIRY = "2026-11-20"


class FakeLive:
    def get_quote(self, ticker):
        return 100.0

    def get_price_history(self, ticker, period="6mo"):
        index = pd.date_range("2026-05-01", periods=120, freq="B", tz="UTC")
        return pd.DataFrame({"Open": 1.0, "Close": np.linspace(90, 100, 120)}, index=index)

    def get_expirations(self, ticker):
        return [EXPIRY, "2026-12-18"]

    def get_option_chain(self, ticker, expiration):
        rows = pd.DataFrame({
            "contractSymbol": ["X1", "X2"], "strike": [100.0, 105.0], "lastPrice": [3.1, 1.2],
            "bid": [3.0, 1.1], "ask": [3.2, 1.3], "impliedVolatility": [0.3, 0.32],
            "volume": [500.0, np.nan], "openInterest": [2000, 15],
            "lastTradeDate": pd.to_datetime(["2026-11-06 19:55", "2026-11-05 15:00"], utc=True)})
        return {"calls": rows, "puts": rows.copy()}

    def get_next_earnings_date(self, ticker):
        return dt.date(2027, 1, 28)

    def get_next_ex_dividend_date(self, ticker):
        return None


@pytest.fixture(autouse=True)
def reset():
    previous = tools.provider
    yield
    clock.unfreeze()
    news.REPLAY = None
    tools.provider = previous


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "fetch_headlines", lambda ticker, timeout=15: [
        Headline("Test Corp beats estimates", "Wire", RECORDED - dt.timedelta(days=2), "https://example.com/a")])
    clock.freeze(RECORDED, RECORDED.date())
    recorder = RecordingProvider(FakeLive())
    tools.provider = recorder
    live_output = tools.get_option_contract.invoke({"ticker": "TEST", "option_type": "call", "strike": 100.0,
                                                    "expiration": EXPIRY})
    recorder.get_price_history("TEST", "6mo")
    recorder.record_headlines("TEST")
    path = recorder.save(tmp_path / "snap.json.gz", [{"ticker": "TEST", "strike": 100.0}])
    clock.unfreeze()
    return path, live_output


def test_replay_returns_what_was_recorded(recorded):
    path, _ = recorded
    replay, live = SnapshotProvider(path), FakeLive()
    assert replay.get_quote("TEST") == 100.0 and replay.get_expirations("TEST") == live.get_expirations("TEST")
    chain, original = replay.get_option_chain("TEST", EXPIRY)["calls"], live.get_option_chain("TEST", EXPIRY)["calls"]
    for column in ("strike", "bid", "ask", "impliedVolatility", "volume", "openInterest", "lastTradeDate"):
        pd.testing.assert_series_equal(chain[column], original[column], check_dtype=False)
    assert "contractSymbol" not in chain  # only the columns the code uses are kept
    assert replay.get_price_history("TEST", "6mo")["Close"].tolist() == pytest.approx(list(np.linspace(90, 100, 120)))
    assert replay.get_next_earnings_date("TEST") == dt.date(2027, 1, 28)
    assert replay.get_next_ex_dividend_date("TEST") is None
    assert replay.contracts == [{"ticker": "TEST", "strike": 100.0}]


def test_a_later_replay_gives_the_same_tool_output(recorded):
    path, live_output = recorded
    clock.freeze(RECORDED + dt.timedelta(days=30), RECORDED.date() + dt.timedelta(days=30))  # weeks later
    tools.provider = SnapshotProvider(path).activate()  # freezes the clock back at the recording time
    replay_output = tools.get_option_contract.invoke({"ticker": "TEST", "option_type": "call", "strike": 100.0,
                                                      "expiration": EXPIRY})
    assert json.loads(replay_output) == json.loads(live_output)
    assert clock.today() == RECORDED.date()


def test_headlines_replay_with_their_age_at_recording_time(recorded):
    path, _ = recorded
    SnapshotProvider(path).activate()
    headlines = FETCH_HEADLINES("TEST")
    assert [h.title for h in headlines] == ["Test Corp beats estimates"]
    assert headlines[0].age_days == pytest.approx(2.0)
    assert FETCH_HEADLINES("OTHER") == []  # not recorded: no headlines, and no live fetch


def test_a_call_that_was_not_recorded_is_a_clear_error(recorded):
    path, _ = recorded
    with pytest.raises(KeyError, match=r"not in snapshot snap.json.gz: get_option_chain\(TEST, 2026-12-18\)"):
        SnapshotProvider(path).get_option_chain("TEST", "2026-12-18")


def test_snapshot_provider_needs_a_path(monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_PATH", "")
    with pytest.raises(ValueError, match="SNAPSHOT_PATH"):
        get_provider("snapshot")
