"""Outcomes, run log and review queue (Checkpoint 6), offline: a temporary log directory, stand-in results."""

import pytest

from options_trade_analyzer import review
from options_trade_analyzer.agents.options_agent import AnalysisResult
from options_trade_analyzer.agents.verifier import Verification

FLAG = {"id": "poor_liquidity", "message": "Liquidity is rated poor (spread)."}
REQUEST = {"ticker": "TEST", "option_type": "call", "strike": 100.0, "expiration": "2026-12-04"}


def result(issues=(), flags=(), findings=None, critic_error=None, invalid=None):
    v = Verification(list(issues), {"llm_critic_error": critic_error})
    return AnalysisResult("a report", [], v, v, findings=findings or {"options_analyst": "ok"},
                          flags=list(flags), invalid_request=invalid)


@pytest.mark.parametrize("kwargs, outcome", [
    ({}, "shown"),
    ({"flags": [FLAG]}, "shown_with_warning"),
    ({"issues": ["Number not found in any tool result: 15.4."]}, "needs_review"),
    ({"critic_error": "no JSON object in the Critic's reply"}, "needs_review"),
    ({"findings": {"market_context": "FAILED: RuntimeError: model timed out"}}, "needs_review"),
    ({"invalid": "no such strike"}, "refused"),
    ({"issues": ["x"], "flags": [FLAG]}, "needs_review"),  # review outranks a warning
])
def test_code_decides_the_outcome(kwargs, outcome):
    assert review.decide_result(result(**kwargs))[0] == outcome


def test_reasons_say_why_a_run_is_held():
    _, reasons = review.decide_result(result(issues=["a", "b"], critic_error="unreadable",
                                             findings={"risk_strategist": "FAILED: timeout"}))
    assert reasons == ["The risk strategist failed, so part of the analysis is missing.",
                       "2 check(s) still fail after the revision rounds.",
                       "The LLM Critic's reply could not be read, so the judgment review did not happen."]


def test_a_run_is_logged_with_its_outcome(tmp_path):
    out = review.run_and_log(REQUEST, {"llm_critic": True}, lambda: result(flags=[FLAG]), log_dir=tmp_path)
    assert out.outcome == "shown_with_warning" and out.run_id
    [logged] = review.runs(tmp_path)
    assert logged["run_id"] == out.run_id and logged["request"] == REQUEST and logged["review"] is None
    assert logged["flags"] == [FLAG] and logged["report"] == "a report"


def test_a_crash_is_logged_for_review_and_raised(tmp_path):
    def boom():
        raise TimeoutError("model did not answer")
    with pytest.raises(TimeoutError):
        review.run_and_log(REQUEST, {}, boom, log_dir=tmp_path)
    [logged] = review.runs(tmp_path)
    assert logged["outcome"] == "needs_review" and "TimeoutError" in logged["reasons"][0]


def test_the_queue_holds_undecided_reviews_oldest_first(tmp_path):
    held = [review.run_and_log(REQUEST, {}, lambda: result(issues=["x"]), log_dir=tmp_path) for _ in range(2)]
    review.run_and_log(REQUEST, {}, lambda: result(), log_dir=tmp_path)  # shown: never queued
    assert [r["run_id"] for r in review.queue(tmp_path)] == [h.run_id for h in held]
    review.log_review(held[0].run_id, "edited", "removed an untraced number", "fixed report", log_dir=tmp_path)
    assert [r["run_id"] for r in review.queue(tmp_path)] == [held[1].run_id]
    decided = next(r for r in review.runs(tmp_path) if r["run_id"] == held[0].run_id)
    assert decided["review"]["decision"] == "edited" and decided["review"]["report"] == "fixed report"
    assert review.escalation_rate(review.runs(tmp_path)) == pytest.approx(2 / 3)


def test_an_edit_needs_the_edited_report(tmp_path):
    with pytest.raises(ValueError):
        review.log_review("abc", "edited", log_dir=tmp_path)


# --- review priority ---

REPORT = "The maximum loss is $520 per contract. Delta is 0.41. The stock last closed at 101.2."


@pytest.mark.parametrize("record, level", [
    ({"issues": ["Number not found in any tool result: $520."]}, "critical"),     # a made-up maximum loss
    ({"issues": ["Number not found in any tool result: 0.41."]}, "high"),         # a made-up Greek
    ({"issues": ["Report contains a recommendation; describe risks only."]}, "critical"),
    ({"issues": ["compute_greeks was called with strike 105, not the requested 100."]}, "critical"),
    ({"issues": ["Missing statement: lower risk does not guarantee a profit."]}, "high"),
    ({"issues": ["Citation [KB: notes.md] does not match any passage retrieved in this run."]}, "medium"),
    ({"issues": ["Something new the verifier says."]}, "high"),                   # unknown: fail safe
    ({"reasons": ["1 headline(s) read like instructions to an AI and were withheld; check that the report "
                  "was not steered."]}, "critical"),
    ({"reasons": ["A data source failed and was not recovered (get_price_trend), so part of the analysis "
                  "is missing."]}, "medium"),
    ({"reasons": ["Market data was missing (implied volatility), so the analysis is low confidence."]}, "low"),
])
def test_priority_follows_the_most_dangerous_problem(record, level):
    assert review.priority({"report": REPORT} | record)["level"] == level


def test_the_worst_problem_decides_and_is_named():
    p = review.priority({"report": REPORT, "issues": ["Number not found in any tool result: 0.41.",
                                                      "Number not found in any tool result: $520."],
                         "reasons": ["Market data was missing (bid/ask), so the analysis is low confidence."]})
    assert p["level"] == "critical" and "$520" in p["why"] and p["count"] == 1


def test_the_queue_puts_dangerous_runs_first_then_oldest(tmp_path):
    def held(issue):
        v = Verification([issue], {})
        return review.run_and_log(REQUEST, {}, lambda: AnalysisResult(REPORT, [], v, v, findings={}), log_dir=tmp_path)
    citation = held("Citation [KB: a.md] does not match any passage retrieved in this run.")
    greek = held("Number not found in any tool result: 0.41.")
    max_loss = held("Number not found in any tool result: $520.")
    greek_later = held("Number not found in any tool result: 101.2.")
    order = [r["run_id"] for r in review.queue(tmp_path)]
    assert order == [max_loss.run_id, greek.run_id, greek_later.run_id, citation.run_id]
