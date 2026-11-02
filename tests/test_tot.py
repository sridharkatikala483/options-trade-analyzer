"""Tree-of-Thought alternative search, offline: a synthetic option chain priced with Black-Scholes."""

import datetime as dt
import json

import pandas as pd
import pytest
from langchain_core.messages import AIMessage

from options_trade_analyzer.agents.tot_search import LLMProposer, Node, RuleProposer, Search, exhaustive
from options_trade_analyzer.agents.verifier import verify
from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.analytics.options_math import bs_price

TODAY = dt.date(2026, 11, 2)
EXPIRATIONS = ["2026-11-13", "2026-11-20", "2026-11-27", "2026-12-18", "2027-03-19"]
SPOT, IV, RATE = 100.0, 0.30, 0.04
ILLIQUID = {("call", 109.0)}  # one thin strike, to exercise pruning


class FakeProvider:
    def get_quote(self, ticker):
        return SPOT

    def get_expirations(self, ticker):
        return EXPIRATIONS

    def get_option_chain(self, ticker, expiration):
        years = alt.years_to_expiry(expiration, TODAY)
        chain = {}
        for kind in ("call", "put"):
            rows = []
            for strike in [float(k) for k in range(80, 121)]:
                price = bs_price(kind, SPOT, strike, years, RATE, IV)
                half = max(0.02, price * 0.02)
                thin = (kind, strike) in ILLIQUID
                rows.append({"strike": strike, "bid": round(max(price - half, 0.01), 2),
                             "ask": round(price + half, 2), "impliedVolatility": IV,
                             "volume": 0 if thin else 800, "openInterest": 3 if thin else 4000})
            chain[f"{kind}s"] = pd.DataFrame(rows)
        return chain


@pytest.fixture
def market():
    return alt.Market(FakeProvider(), "TEST", RATE, today=TODAY)


def run(market, option_type="call", strike=102.0, proposer=None):
    search = Search(market, option_type, strike, EXPIRATIONS[0], proposer or RuleProposer(), "2026-11-05")
    return search.run()


def test_weights_sum_to_100_and_points_add_up(market):
    base = alt.original("call", 102.0, EXPIRATIONS[0], market)
    spread = alt.build("bull call spread", (102.0, 104.0), EXPIRATIONS[0], market)
    e = alt.evaluate(spread, base, market, bullish=True)
    assert sum(alt.WEIGHTS.values()) == 100
    assert e.score == pytest.approx(sum(e.points.values()), abs=0.11)
    assert e.max_loss < alt.evaluate(base, base, market, True).max_loss
    assert e.iv_drop_change > alt.iv_drop_change(base, market)  # the short leg offsets the volatility drop
    assert e.pruned is None


def test_pruning_rules(market):
    base = alt.original("call", 102.0, EXPIRATIONS[0], market)
    assert alt.evaluate(base, base, market, True).pruned == "maximum loss is not lower than the original"
    thin = alt.build("bull call spread", (102.0, 109.0), EXPIRATIONS[0], market)
    assert alt.evaluate(thin, base, market, True).pruned == "a leg has poor liquidity"
    assert "no two-sided quote" in alt.build("bull call spread", (102.0, 150.0), EXPIRATIONS[0], market)


def test_ties_go_to_lower_max_loss(market):
    base = alt.original("call", 102.0, EXPIRATIONS[0], market)
    a = alt.evaluate(alt.build("bull call spread", (102.0, 105.0), EXPIRATIONS[0], market), base, market, True)
    b = alt.evaluate(alt.build("bull call spread", (102.0, 107.0), EXPIRATIONS[0], market), base, market, True)
    a.score, b.score = 70.0, 71.5  # within 2 points: lower maximum loss wins despite the lower score
    assert alt.rank([b, a])[0] is a
    b.score = 72.5
    assert alt.rank([a, b])[0] is b


def test_search_finds_a_lower_risk_alternative_within_limits(market):
    result = run(market)
    selected, original = result["selected"], result["original"]
    assert result["outcome"] == "alternative found"
    assert selected["max_loss"] < original["max_loss"]
    assert selected["score"] >= alt.MIN_SCORE
    assert result["runner_up"]["strategy"] != selected["strategy"] or \
        result["runner_up"]["expiration"] != selected["expiration"]
    assert result["search"]["nodes_scored"] <= 24
    assert result["search"]["option_chains_loaded"] <= 3
    assert result["search"]["stop"] == "searched all levels"
    assert "109 call" not in json.dumps(selected)  # the illiquid strike never wins


def test_search_is_deterministic(market):
    first = run(market)
    second = run(alt.Market(FakeProvider(), "TEST", RATE, today=TODAY))
    assert first == second


def test_beam_matches_exhaustive_search(market):
    best = exhaustive(market, "call", 102.0, EXPIRATIONS[0])[0]
    assert run(market)["selected"]["score"] == best.score


def test_put_search_uses_bearish_families(market):
    result = run(market, "put", 98.0)
    assert result["selected"]["strategy"].split(" ")[0] in ("bear", "cheaper")
    assert result["selected"]["max_loss"] < result["original"]["max_loss"]


def test_families_are_pruned_only_for_objective_reasons_and_kept_alive(market):
    search = Search(market, "call", 102.0, EXPIRATIONS[0], RuleProposer())
    state = search.build_graph().invoke({"depth": 0, "frontier": [0], "nodes": [Node(0, None, 0)], "stop": None})
    nodes = state["nodes"]
    depth_one = {n.family: n.pruned for n in nodes if n.depth == 1}
    assert set(depth_one) == set(alt.FAMILIES_FOR["call"])
    # here a short put at the 102 strike risks more than the 102 call costs, so that family is pruned
    assert depth_one["bull put spread"] == "maximum loss is not lower than the original"
    # the beam's picks at depth 2 are the parents of depth-3 nodes: both surviving families stay alive
    kept = {nodes[n.parent].family for n in nodes if n.depth == 3}
    assert kept == {"bull call spread", "cheaper call"}


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def invoke(self, prompt):
        return AIMessage(content=self.replies.pop(0) if self.replies else "")


def test_llm_proposals_are_validated_against_the_menu():
    llm = FakeLLM(['Sure: {"choices": [2, 9, 2, "x"], "reason": "wider room"}', "not json"])
    proposer = LLMProposer(llm)
    assert proposer.propose("q", "c", ["a", "b", "c"], [0, 1, 2], 3) == ([1], "wider room")
    picks, reason = proposer.propose("q", "c", ["a", "b", "c"], [0, 1, 2], 2)
    assert picks == [0, 1] and reason.startswith("fallback")
    assert (proposer.calls, proposer.fallbacks) == (2, 1)


def test_search_survives_an_unusable_llm(market):
    result = run(market, proposer=LLMProposer(FakeLLM([])))
    assert result["outcome"] == "alternative found"
    assert result["search"]["llm_fallbacks"] == result["search"]["llm_proposals"] >= 4


def test_verifier_accepts_the_searched_expiration_and_requires_the_tool(market):
    result = run(market)
    selected = result["selected"]
    request = {"ticker": "TEST", "option_type": "call", "strike": 102, "expiration": EXPIRATIONS[0]}
    trace = [{"step": "Observation", "tool": "search_alternatives", "args": {}, "text": json.dumps(result)}]
    report = f"Lower-risk alternative: {selected['strategy']} expiring {selected['expiration']}, maximum loss ${selected['max_loss']}."
    v = verify(report, trace, request, use_retrieval=False, use_tot=True)
    assert not any("Date" in i or "Number" in i for i in v.issues), v.issues
    assert any("compare_strategies" in i for i in verify(report, trace, request, False).issues)
    assert not any("search_alternatives" in i for i in v.issues)


class ThinFirstExpiration(FakeProvider):
    """Every quote on the original expiration is thin, like a quiet mid-week weekly."""

    def get_option_chain(self, ticker, expiration):
        chain = super().get_option_chain(ticker, expiration)
        if expiration == EXPIRATIONS[0]:
            for df in chain.values():
                df["volume"], df["openInterest"] = 0, 3
        return chain


def test_thin_original_expiration_does_not_prune_every_family():
    market = alt.Market(ThinFirstExpiration(), "TEST", RATE, today=TODAY)
    result = run(market)
    assert result["outcome"] == "alternative found"
    assert result["selected"]["expiration"] != EXPIRATIONS[0]
    assert result["selected"]["score"] == exhaustive(market, "call", 102.0, EXPIRATIONS[0])[0].score
