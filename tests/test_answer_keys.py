"""Answer keys and report scoring, offline: synthetic facts and short reports with planted mistakes."""

import datetime as dt
import json

import pytest

from options_trade_analyzer import answer_keys as ak
from options_trade_analyzer.agents import tools

CONTRACT = {"ticker": "TEST", "option_type": "call", "strike": 100.0, "expiration": "2026-11-20"}
FACTS = {"max_loss": 752.5, "breakeven": 107.53, "days_to_expiry": 14, "liquidity": "good",
         "earnings_date": "2027-01-28", "earnings_before_expiry": False, "market_closed": True, "ex_dividend_flag": True}
SAME_EXPIRY = [{"step": "Observation", "tool": "search_alternatives", "text": json.dumps(
    {"selected": {"strategy": "bull call spread 100/105", "expiration": "2026-11-20"}})}]
GOOD = """Summary: buying the TEST 100 call costs 752.5 per contract, the maximum loss, with only 14 days left.
The breakeven is 107.53. Liquidity is rated good. Time decay (theta) costs money every day.
Earnings on 2027-01-28 fall after expiry, so they cannot affect this option.
The quote is from a closed market. An ex-dividend date falls before expiry.
Black-Scholes only approximates American-style options.
A bull call spread 100/105 lowers the maximum loss, but lower risk does not guarantee a profit."""


def key(facts=FACTS):
    return {"contract": CONTRACT, "facts": facts, "items": [vars(i) for i in ak.items_for(facts)]}


def test_a_complete_sound_report_scores_full_marks():
    result = ak.score(GOOD, key(), SAME_EXPIRY)
    # 11 musts: the alternative-expiration item does not apply when the alternative keeps the expiration
    assert result == {"must_met": 11, "must_total": 11, "mistakes": 0, "missing": [], "made": []}


@pytest.mark.parametrize("planted, missing, made", [
    ("Earnings on 2027-01-28, after expiry, may impact volatility.", [], ["earnings_as_risk"]),
    ("The bid-ask spread is wide and volume is low.", [], ["liquidity_contradiction"]),
    ("You should buy this call.", [], ["recommendation"]),
])
def test_planted_mistakes_are_caught(planted, missing, made):
    result = ak.score(GOOD + "\n" + planted, key(), SAME_EXPIRY)
    assert result["made"] == made and result["missing"] == missing


def test_missing_facts_are_listed():
    report = GOOD.replace("752.5", "a lot").replace("only 14 days left", "a few weeks left")
    assert ak.score(report, key(), SAME_EXPIRY)["missing"] == ["max_loss", "days_left"]


def test_a_rounded_whole_number_does_not_count_as_a_price_with_cents():
    assert ak._has_number("the 14 call", 14.19) is False
    assert ak._has_number("the 107 strike", 107.53) is False
    assert ak._has_number("a breakeven of $107.53", 107.53) and ak._has_number("$753 at most", 752.5)


def test_earnings_before_expiry_needs_the_volatility_drop():
    facts = FACTS | {"earnings_date": "2026-11-17", "earnings_before_expiry": True}
    with_drop = GOOD + "\nEarnings on 2026-11-17 come before expiry; a volatility crush could cut the price."
    assert "earnings_before" not in ak.score(with_drop, key(facts), SAME_EXPIRY)["missing"]
    assert "earnings_before" in ak.score(GOOD, key(facts), SAME_EXPIRY)["missing"]
    assert "earnings_as_risk" not in [i.id for i in ak.items_for(facts)]


def test_an_alternative_on_another_expiration_must_give_its_date():
    later = [{"step": "Observation", "tool": "search_alternatives", "text": json.dumps(
        {"selected": {"strategy": "bull call spread 100/105", "expiration": "2026-12-18"}})}]
    assert "alternative_expiration" in ak.score(GOOD, key(), later)["missing"]
    assert ak.score(GOOD + " The spread expires Dec 18.", key(), later)["missing"] == []
    assert ak.score(GOOD, key(), [])["must_total"] == 10  # no alternative search in this run: not scored


def test_generic_descriptions_cover_every_contract_specific_item():
    # an item whose description quotes a value must have contract-free wording for cross-contract summaries
    facts = FACTS | {"liquidity": "poor", "earnings_before_expiry": True}
    for facts_ in (FACTS, facts):
        for item in ak.items_for(facts_):
            if any(str(v) in item.description for v in facts_.values() if v not in (True, False, None)):
                assert item.id in ak.GENERIC, item.id


def test_build_key_reads_the_tools(monkeypatch):
    class Stub:
        def invoke(self, args):
            return json.dumps({"max_loss_per_contract": 231.5, "breakeven": 98.31, "days_to_expiry": 35,
                               "data_quality": {"liquidity": {"rating": "poor"}, "quote": {"status": "open"},
                                                "model_assumption_flags": []}})

    class Provider:
        def get_next_earnings_date(self, ticker):
            return dt.date(2026, 12, 1)

    monkeypatch.setattr(tools, "get_option_contract", Stub())
    k = ak.build_key(Provider(), CONTRACT | {"expiration": "2026-12-11"})
    ids = [i["id"] for i in k["items"]]
    assert k["facts"]["earnings_before_expiry"] is True and "earnings_before" in ids
    assert "liquidity_overstated" in ids and "days_left" not in ids and "stale_quote" not in ids
