"""The verifier must catch the failures seen in real runs and pass a faithful report.

Fixtures reproduce the AAPL 350 call (Nov 6, 2026) tool outputs. FLAWED_REPORT copies the key
mistakes from the run after the Checkpoint 2 changes: an invented 350/355 spread, a fake knowledge
citation, a "no headlines" claim without searching, numbers it calculated itself, and a liquidity
remark contradicting the 'good' rating.
"""

import json

import pytest

from options_trade_analyzer.agents import verifier
from options_trade_analyzer.agents.verifier import verify

REQUEST = {"ticker": "AAPL", "option_type": "call", "strike": 350, "expiration": "2026-11-06"}

CONTRACT = {
    "stock_price": 347.73, "premium": 7.5, "bid": 7.35, "ask": 7.65, "spread_pct_of_premium": 4.0,
    "implied_volatility_pct": 33.3, "volume": 791, "open_interest": 5461, "days_to_expiry": 13,
    "breakeven": 357.5, "max_loss_per_contract": 750.0,
    "data_quality": {
        "quote": {"last_trade": "2026-10-23 15:59 ET", "age_hours": 32.2, "status": "market closed"},
        "liquidity": {"rating": "good", "issues": []},
        "model_vs_market": {"model_price": 8.05, "market_mid": 7.5, "model_minus_mid_pct": 7.3,
                            "model_within_bid_ask": False, "gap_flag": True},
        "model_assumption_flags": ["earnings before expiration: post-earnings prices are scenarios"],
    },
}
GREEKS = {"implied_volatility_pct": 33.3, "model_price": 8.06, "delta": 0.4815, "theta": -0.3462,
          "theta_per_contract_per_day": -34.62}
GREEKS_DROP = {"implied_volatility_pct": 19.98, "model_price": 4.51, "theta_per_contract_per_day": -21.31}
EARNINGS = {"ticker": "AAPL", "next_earnings_date": "2026-11-02"}
STRATEGIES = {"stock_price": 347.73, "strategies": [
    {"strategy": "long 350 call", "cost": 750.0, "max_loss": 750.0, "max_gain": "unlimited",
     "breakevens": [357.5], "payoff_at_expiry": {"350.00": -750.0, "360.00": 250.0}},
    {"strategy": "bull call spread 350/360", "legs": ["buy 1 350 call @ 7.50", "sell 1 360 call @ 3.45"],
     "cost": 405.0, "max_loss": 405.0, "max_gain": 595.0, "breakevens": [354.05],
     "payoff_at_expiry": {"350.00": -405.0, "360.00": 595.0}},
]}
KNOWLEDGE = {"results": [{"source": "earnings-volatility-crush#2", "text": "..."},
                         {"source": "time-decay-theta#2", "text": "..."}]}
NEWS = {"results": [{"headline": "Apple Faces 'Slightly Challenging' Earnings Setup", "source": "Yahoo Finance",
                     "date": "2026-10-24"}]}


def obs(tool: str, result: dict, args: dict | None = None) -> dict:
    return {"step": "Observation", "tool": tool, "args": args or {}, "text": json.dumps(result)}


CORE_TRACE = [
    obs("get_option_contract", CONTRACT),
    obs("compute_greeks", GREEKS),
    obs("get_earnings_date", EARNINGS),
    obs("compute_greeks", GREEKS_DROP, {"iv_change_pct": -40}),
]
FULL_TRACE = CORE_TRACE + [
    obs("compare_strategies", STRATEGIES),
    obs("search_options_knowledge", KNOWLEDGE),
    obs("search_recent_news", NEWS),
]

FLAWED_REPORT = """Summary: AAPL is $347.73 and the premium is $7.50. Earnings are on 2026-11-02.
Data quality: liquidity "good"; model vs market gap $0.56 (7.3%).
Main risks: Volatility crush could reduce value by ~44% [KB: volatility crush after earnings].
While rated "good," low volume (791) could widen spreads.
Lower-risk alternative: a bull call spread (buy 350 call, sell 355 call) would cost $2.25, max gain $2.75,
breakeven $352.25.
What to watch: No relevant headlines found [News: none]."""

GOOD_REPORT = """Summary: AAPL is $347.73; the 350 call costs $7.50 with breakeven $357.50 and 13 days left.
Earnings are on 2026-11-02, before expiration on 2026-11-06.
Key numbers: implied volatility 33.3%, theta -$34.62 per contract per day, model price $8.06.
Data quality: market closed (last trade 2026-10-23 15:59 ET); liquidity rating good (4.0% spread,
791 volume, 5,461 open interest); model $8.05 vs market mid $7.50 (+7.3%).
Main risks: after a volatility drop to 19.98% the scenario model price is $4.51 [KB: earnings-volatility-crush#2];
time decay [KB: time-decay-theta#2].
Lower-risk alternative: the 350/360 bull call spread costs $405, max loss $405, max gain $595,
breakeven $354.05. Lower risk does not guarantee a profit.
What to watch: earnings setup [News: Yahoo Finance, 2026-10-24].
Limits: Black-Scholes only approximates this American-style option."""


def test_flawed_run_is_caught():
    v = verify(FLAWED_REPORT, CORE_TRACE, REQUEST, use_retrieval=True)
    text = " ".join(v.issues)
    assert not v.passed
    for tool in ("compare_strategies", "search_options_knowledge", "search_recent_news"):
        assert f"Required tool not called: {tool}" in text
    for invented in ("$2.25", "$2.75", "$352.25", "$0.56", "44%"):
        assert invented in text
    assert "liquidity" in text.lower()
    assert "[KB: volatility crush after earnings]" in text
    assert "[News: none]" in text
    assert v.metrics["tool_completeness"] < 0.6
    assert v.metrics["citation_accuracy"] == 0


def test_faithful_report_passes():
    v = verify(GOOD_REPORT, FULL_TRACE, REQUEST, use_retrieval=True)
    assert v.passed, v.issues
    assert v.metrics["citation_accuracy"] == 1.0
    assert v.metrics["tool_completeness"] == 1.0


def test_wrong_earnings_date_is_flagged():
    report = GOOD_REPORT.replace("Earnings are on 2026-11-02", "Earnings are on October 28")
    v = verify(report, FULL_TRACE, REQUEST, use_retrieval=True)
    assert any("2026-10-28" in issue and "2026-11-02" in issue for issue in v.issues)


def test_missing_volatility_scenario_is_flagged_when_earnings_precede_expiry():
    trace = [s for s in FULL_TRACE if s["args"].get("iv_change_pct") is None]
    v = verify(GOOD_REPORT.replace("$4.51", "a lower value").replace("19.98%", "a lower level"),
               trace, REQUEST, use_retrieval=True)
    assert any("iv_change_pct" in issue for issue in v.issues)


def test_retrieval_tools_not_required_without_retrieval():
    report = GOOD_REPORT.split("[KB:")[0] + "."
    v = verify(report, CORE_TRACE + [obs("compare_strategies", STRATEGIES)], REQUEST, use_retrieval=False)
    assert v.metrics["missing_tools"] == 0


def test_recommendation_is_flagged():
    v = verify(GOOD_REPORT + "\nI recommend buying this call.", FULL_TRACE, REQUEST, use_retrieval=True)
    assert any("recommendation" in issue for issue in v.issues)


def test_greeks_called_with_wrong_stock_price_is_flagged():
    wrong = obs("compute_greeks", GREEKS, {"stock_price": 195.22, "implied_volatility_pct": 33.3, "strike": 350,
                                           "expiration": "2026-11-06"})
    trace = [FULL_TRACE[0], wrong] + FULL_TRACE[2:]
    v = verify(GOOD_REPORT, trace, REQUEST, use_retrieval=True)
    assert any("195.22" in issue for issue in v.issues)
    assert v.metrics["tool_input_errors"] == 1


def test_numbers_from_tool_inputs_do_not_count_as_support():
    trace = FULL_TRACE + [obs("compute_greeks", GREEKS, {"stock_price": 195.22})]
    v = verify(GOOD_REPORT + "\nThe stock was $195.22.", trace, REQUEST, use_retrieval=True)
    assert any("$195.22" in issue for issue in v.issues)


def test_wrong_day_count_is_flagged_but_correct_one_passes():
    assert verify(GOOD_REPORT, FULL_TRACE, REQUEST, use_retrieval=True).passed  # "13 days" is days_to_expiry
    v = verify(GOOD_REPORT + "\nEarnings come 12 days before expiry.", FULL_TRACE, REQUEST, use_retrieval=True)
    assert any("12 days" in issue for issue in v.issues)



# --- required statements (the answer keys found these missing in about half of qwen3's reports) ---

LIMITS = "Black-Scholes only approximates this American-style option."
NO_PROFIT = "Lower risk does not guarantee a profit."


def test_missing_model_limits_and_no_guarantee_are_flagged():
    problems = verifier.statement_problems("Summary: a call.", has_alternative=True)
    assert len(problems) == 2 and all(p.startswith("Missing statement") for p in problems)
    assert verifier.statement_problems(f"{LIMITS} {NO_PROFIT}", has_alternative=True) == []


def test_no_guarantee_is_required_only_when_an_alternative_was_searched():
    assert verifier.statement_problems(LIMITS, has_alternative=False) == []


def test_a_missing_statement_goes_back_to_the_writer():
    from options_trade_analyzer.agents.team import route
    assert list(route(verifier.statement_problems("Summary.", has_alternative=True))) == ["writer"]


# --- overconfident wording (Lab 6.1 during-generation check) ---

@pytest.mark.parametrize("sentence", [
    "The stock will rise above the breakeven.",
    "This spread is risk-free.",
    "Volatility crush: No risk (earnings are after expiration).",  # the one real case in the 30 reports
    "Profit is guaranteed with this spread.",
    "The option will certainly expire in the money.",
])
def test_overconfident_sentences_are_flagged(sentence):
    assert verifier.overconfident_sentences(sentence) == [sentence]


@pytest.mark.parametrize("sentence", [
    "Lower risk does not guarantee a profit.",
    "In this scenario, the price could fall to $4.51.",
    "Model assumes volatility will drop post-earnings, but this is a scenario, not a forecast.",
    "Always verify with up-to-date data.",
])
def test_hedged_or_required_sentences_pass(sentence):
    assert verifier.overconfident_sentences(sentence) == []


def test_known_gap_a_conditional_certainty_is_not_flagged():
    # "if" counts as hedging so conditional explanations pass; the LLM Critic must catch this kind
    assert verifier.overconfident_sentences("Profit is guaranteed if the trend holds up.") == []


def test_overconfident_wording_goes_back_to_the_writer():
    from options_trade_analyzer.agents.team import route
    issue = f"Overconfident wording; describe it as a possibility, scenario or estimate: \"x\""
    assert list(route([issue])) == ["writer"]
