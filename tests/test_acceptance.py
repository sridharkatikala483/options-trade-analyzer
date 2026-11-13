"""Acceptance gate (Week 5 feedback): thresholds, measures from saved runs, hand-confirmed false alarms."""

import json

from options_trade_analyzer import acceptance

CONTRACT = {"ticker": "TEST", "strike": 100.0, "option_type": "call", "expiration": "2026-11-20"}
CLEAN = {"tool_completeness": 1.0, "unsupported_numbers": 0, "date_errors": 0, "invalid_citations": 0,
         "recommendation": False}


def run(seconds=40, **final):
    return {"contract": CONTRACT, "setup": "team", "seconds": seconds, "final": CLEAN | final,
            "final_issues": [], "findings": {}, "outcome": "shown"}


def score(made=(), met=10, total=10):
    return {"contract": CONTRACT, "setup": "team", "must_met": met, "must_total": total, "made": list(made)}


def verdicts(measures):
    return {t.key: ok for t, _, ok in acceptance.gate(measures)}


def test_a_clean_fast_run_passes_every_threshold():
    assert all(verdicts(acceptance.measure([run()], [score()], set())).values())


def test_each_failure_is_named():
    m = acceptance.measure([run(seconds=900, unsupported_numbers=1, recommendation=True) | {"outcome": "needs_review"}],
                           [score(made=["earnings_as_risk"], met=8)], set())
    failed = {k for k, ok in verdicts(m).items() if not ok}
    assert failed == {"unsupported_numbers", "recommendations", "judgment_errors_per_10", "facts_pct",
                      "held_pct", "avg_seconds"}


def test_a_hand_confirmed_false_alarm_is_not_a_judgment_error():
    ruled_out = {("TEST 100 call 2026-11-20", "team", "earnings_as_risk")}
    m = acceptance.measure([run()], [score(made=["earnings_as_risk"])], ruled_out)
    assert m["judgment_errors_per_10"] == 0


def test_false_alarms_are_read_per_results_file(tmp_path):
    path = tmp_path / "hand_checks.json"
    path.write_text(json.dumps([
        {"results": "a", "contract": "X", "setup": "s", "item": "i", "verdict": "false_alarm", "note": "n"},
        {"results": "a", "contract": "Y", "setup": "s", "item": "i", "verdict": "real", "note": "n"},
        {"results": "b", "contract": "Z", "setup": "s", "item": "i", "verdict": "false_alarm", "note": "n"}]))
    assert acceptance.false_alarms("a", path) == {("X", "s", "i")}


def test_every_ruled_out_flag_in_the_repo_has_a_note():
    entries = json.loads(acceptance.HAND_CHECKS.read_text())
    assert entries and all(e["note"].strip() and e["verdict"] in ("false_alarm", "real") for e in entries)


def test_the_table_gives_an_overall_verdict_per_setup():
    good = acceptance.measure([run()], [score()], set())
    bad = acceptance.measure([run(seconds=999)], [score()], set())
    assert acceptance.table({"good": good, "slow": bad})[-1] == "| **All thresholds** | | **pass** | **fail** |"
