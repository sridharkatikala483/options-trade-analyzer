"""Multi-agent team wiring, offline: the LLM calls (run_agent, write_report) are replaced by stand-ins
that return scripted tool traces, so these tests check the graph, the routing and failure handling."""

import json
import math

import pandas as pd
import pytest

from options_trade_analyzer.agents import team, tools
from options_trade_analyzer.agents.critic import Judgment
from options_trade_analyzer.analytics.trend import price_trend

REQUEST = {"ticker": "TEST", "option_type": "call", "strike": 105.0, "expiration": "2026-12-04"}
CONTRACT = {"ticker": "TEST", "stock_price": 100.0, "premium": 6.83, "breakeven": 111.83,
            "max_loss_per_contract": 683.0, "implied_volatility_pct": 30.0,
            "data_quality": {"liquidity": {"rating": "fair"}}}
GOOD_REPORT = ("Summary: the premium is $6.83 and the breakeven is $111.83. Lower risk does not guarantee a profit. "
               "Black-Scholes only approximates this American-style option.")


def obs(agent, tool, result):
    return {"step": "Observation", "tool": tool, "args": {}, "text": json.dumps(result), "agent": agent}


class Script:
    """Stand-in for the LLM calls; records every call so tests can check order and routing."""

    def __init__(self, earnings="2027-01-27", skip_news_first=False, fail=(), reports=(GOOD_REPORT,),
                 judgments=()):
        self.calls, self.earnings, self.skip_news_first, self.fail = [], earnings, skip_news_first, set(fail)
        self.reports, self.writer_inputs = list(reports), []
        self.judgments = list(judgments)  # one list of Judgments per LLM Critic call; then none

    def run_agent(self, name, prompt, agent_tools, messages):
        self.calls.append(name)
        if name in self.fail:
            return team.AgentRun(name, messages, error="RuntimeError: model timed out")
        trace = {
            "options_analyst": [obs(name, "compute_greeks", {"delta": 0.4}),
                                obs(name, "search_options_knowledge", {"results": []})],
            "market_context": [obs(name, "get_price_trend", {"trend": "up"}),
                               obs(name, "get_earnings_date", {"next_earnings_date": self.earnings})]
                              + ([] if self.skip_news_first and self.calls.count(name) == 1
                                 else [obs(name, "search_recent_news", {"results": []})]),
            "risk_strategist": [obs(name, "search_alternatives", {"outcome": "alternative found"})],
        }[name]
        return team.AgentRun(name, messages + ["(reply)"], f"{name} findings", trace, {"input": 10, "output": 2})

    def llm_review(self, context, report):
        self.calls.append("llm_critic")
        return (self.judgments.pop(0) if self.judgments else []), None, {"input": 7, "output": 1}

    def write_report(self, messages):
        self.calls.append("writer")
        self.writer_inputs.append(messages[1].content)
        return (self.reports.pop(0) if len(self.reports) > 1 else self.reports[0]), {"input": 5, "output": 5}


class FakeContractTool:
    def __init__(self, result):
        self.result = result

    def invoke(self, args):
        return json.dumps(self.result)


@pytest.fixture
def script(monkeypatch):
    def install(**kwargs):
        s = Script(**kwargs)
        monkeypatch.setattr(team, "run_agent", s.run_agent)
        monkeypatch.setattr(team, "write_report", s.write_report)
        monkeypatch.setattr(team, "llm_review", s.llm_review)
        monkeypatch.setattr(tools, "get_option_contract", FakeContractTool(CONTRACT))
        return s
    return install


def run(**kwargs):
    return team.analyze_contract_team(**REQUEST, **kwargs)


def test_specialists_run_in_parallel_then_risk_writer_critic(script):
    s = script()
    result = run()
    assert set(s.calls[:2]) == {"options_analyst", "market_context"}  # both before the join
    assert s.calls[2:] == ["risk_strategist", "writer", "llm_critic"]
    assert result.verification.passed and result.revisions == 0
    assert set(result.findings) == set(team.SPECIALISTS)
    assert result.tokens == {"input": 42, "output": 12}
    assert {step.get("agent") for step in result.trace} >= {"coordinator", *team.SPECIALISTS, "writer"}


def test_a_missing_tool_goes_back_to_its_owner_only(script):
    s = script(skip_news_first=True)
    result = run()
    assert result.first_draft_verification.issues == ["Required tool not called: search_recent_news."]
    assert result.routing == [{"round": 1, "agent": "market_context",
                               "issues": ["Required tool not called: search_recent_news."]}]
    assert s.calls.count("market_context") == 2 and s.calls.count("options_analyst") == 1
    assert result.verification.passed and result.revisions == 1


def test_a_wording_problem_goes_to_the_writer_only(script):
    s = script(reports=("Summary: the premium is $9.99.", GOOD_REPORT))
    result = run()
    assert result.routing[0]["agent"] == "writer"
    assert s.calls.count("writer") == 2 and s.calls.count("risk_strategist") == 1
    assert result.verification.passed


def test_a_failed_specialist_is_reported_and_the_loop_still_ends(script):
    s = script(fail={"market_context"})
    result = run()
    assert "Market Context: FAILED" in s.writer_inputs[0]
    assert result.findings["market_context"].startswith("FAILED")
    assert result.revisions == team.MAX_REVISIONS  # tools stay missing; the cap stops the loop
    assert s.calls.count("market_context") == 1  # a failed agent is not retried
    assert not result.verification.passed


def test_an_invalid_request_stops_at_the_coordinator(script, monkeypatch):
    s = script()
    monkeypatch.setattr(tools, "get_option_contract", FakeContractTool({"error": "strike 105.0 not listed"}))
    result = run()
    assert s.calls == [] and "strike 105.0 not listed" in result.report


def test_the_volatility_drop_step_depends_on_the_earnings_date():
    t = team.Team(REQUEST)
    market = lambda date: team.AgentRun("market_context", trace=[obs("market_context", "get_earnings_date",  # noqa: E731
                                                                      {"next_earnings_date": date})])
    before, _ = t._risk_prompt({"contract": CONTRACT, "runs": {"market_context": market("2026-11-20")}})
    after, _ = t._risk_prompt({"contract": CONTRACT, "runs": {"market_context": market("2027-01-27")}})
    assert "iv_change_pct=-40" in before and "iv_change_pct" not in after


def test_route():
    routed = team.route(["Required tool not called: compute_greeks (iv_change_pct).",
                         "Required tool not called: get_earnings_date.",
                         "search_alternatives was called with strike 100, not the requested 105.",
                         "Number not found in any tool result: 9.99."])
    assert routed == {"risk_strategist": ["Required tool not called: compute_greeks (iv_change_pct).",
                                          "search_alternatives was called with strike 100, not the requested 105."],
                      "market_context": ["Required tool not called: get_earnings_date."],
                      "writer": ["Number not found in any tool result: 9.99."]}


def test_price_trend():
    rising = price_trend(pd.Series([100 * math.exp(0.005 * i) for i in range(120)]))
    assert rising["trend"] == "up" and rising["above_sma_50"] and rising["change_1m_pct"] > 2
    flat = price_trend(pd.Series([50.0] * 120))
    assert flat["trend"] == "sideways" and flat["change_3m_pct"] == 0.0 and flat["high_3m"] == 50.0
    assert "error" in price_trend(pd.Series([50.0] * 10))


def test_the_llm_critic_runs_only_after_the_rules_pass(script):
    s = script(reports=("Summary: the premium is $9.99.", GOOD_REPORT))
    run()
    assert s.calls.index("llm_critic") > s.calls.index("writer", s.calls.index("writer") + 1)
    assert s.calls.count("llm_critic") == 1  # not on the draft that failed the rules


def test_a_judgment_problem_goes_to_the_agent_the_critic_names(script):
    flagged = [Judgment("risk_strategist", "The alternative expires Dec 18, not Dec 4, and the findings omit it.")]
    s = script(judgments=[flagged])
    result = run()
    assert result.first_draft_verification.metrics["judgment_issues"] == 1
    assert result.routing[0]["agent"] == "risk_strategist"
    assert result.routing[0]["issues"][0].startswith("Judgment issue for risk_strategist:")
    assert s.calls.count("risk_strategist") == 2 and s.calls.count("writer") == 2
    assert result.verification.passed and result.revisions == 1


def test_the_llm_critic_can_be_switched_off(script):
    s = script(judgments=[[Judgment("writer", "would have been flagged")]])
    result = run(use_llm_critic=False)
    assert "llm_critic" not in s.calls and result.verification.passed
    assert result.verification.metrics["llm_critic_ran"] is False


def test_a_critic_that_never_agrees_still_stops_at_the_cap(script):
    always = [[Judgment("writer", "still unclear")]] * 5
    s = script(judgments=always)
    result = run()
    assert result.revisions == team.MAX_REVISIONS and s.calls.count("llm_critic") == team.MAX_REVISIONS + 1
    assert not result.verification.passed


def test_progress_is_reported_as_each_agent_finishes(script):
    script()
    steps = []
    run(on_step=lambda node, update: steps.append(node))
    assert steps[0] == "coordinator" and set(steps[1:3]) == {"options_analyst", "market_context"}
    assert steps[3:] == ["risk_strategist", "writer", "critic"]
