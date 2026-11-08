"""Background analysis jobs, offline: a stand-in run reports steps from a thread."""

import threading

import pytest

from options_trade_analyzer.agents.verifier import Verification
from options_trade_analyzer.jobs import Job, Jobs


def wait(job: Job, timeout: float = 5) -> None:
    for _ in range(int(timeout * 100)):
        if job.done:
            return
        threading.Event().wait(0.01)
    raise AssertionError("job did not finish")


def test_now_working_follows_the_graph():
    job = Job(("X",), "X", llm_critic=True)
    assert job.now_working() == "Coordinator is looking up the contract"
    job.record("coordinator", {})
    assert job.now_working() == "Options Analyst and Market Context are working"
    job.record("market_context", {})
    assert job.now_working() == "Options Analyst is working"
    job.record("options_analyst", {})
    assert job.now_working().startswith("Risk Strategist is working")
    job.record("risk_strategist", {})
    assert job.now_working() == "Writer is drafting the report"
    job.record("writer", {})
    assert job.now_working().startswith("Critic is checking the report (rules first, then the LLM review")
    job.record("critic", {"checks": [Verification(issues=["Number not found in any tool result: 9.99."])]})
    assert job.steps[-1][2] == "Critic checked the report: 1 issue(s) found"
    assert job.now_working() == "The agents responsible are fixing the Critic's issues"
    job.record("revise", {"revisions": 1})
    assert job.now_working() == "Writer is revising the report"


def test_a_job_runs_in_the_background_and_keeps_its_result():
    release = threading.Event()

    def run(on_step):
        on_step("coordinator", {})
        release.wait(5)
        return "the report"

    jobs = Jobs()
    job = jobs.start(("AAPL",), "AAPL 345 call", True, run)
    assert jobs.running() is job and not job.done
    with pytest.raises(RuntimeError, match="AAPL 345 call is already running"):
        jobs.start(("MSFT",), "MSFT 550 call", True, run)  # one at a time
    release.set()
    wait(job)
    assert job.result == "the report" and job.error is None and jobs.running() is None
    assert [node for _, node, _ in job.steps] == ["coordinator"]
    assert jobs.by_key[("AAPL",)] is job  # still there for the next page load


def test_a_failed_run_is_recorded_not_lost():
    def run(on_step):
        raise ConnectionError("Ollama is not running")

    job = Jobs().start(("X",), "X", False, run)
    wait(job)
    assert job.error == "ConnectionError: Ollama is not running" and job.result is None
