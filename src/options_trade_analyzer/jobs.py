"""Background analysis runs for the dashboard.

A team run takes minutes on a local model. Run inside a Streamlit page, any click or reload would
cancel it, so the dashboard starts it here instead: in a thread, with progress recorded on a Job that
outlives the page. One run at a time, because the local model serves one request at a time anyway.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

FINISHED = {
    "coordinator": "Coordinator looked up the contract and froze the market data",
    "options_analyst": "Options Analyst finished: price, Greeks, liquidity",
    "market_context": "Market Context finished: trend, earnings date, news",
    "risk_strategist": "Risk Strategist finished: worst case and lower-risk alternative",
    "writer": "Writer drafted the report",
    "critic": "Critic checked the report",
    "revise": "The agents responsible fixed the Critic's issues",
}
TITLES = {"options_analyst": "Options Analyst", "market_context": "Market Context"}


@dataclass
class Job:
    key: tuple
    label: str
    llm_critic: bool
    started: float = field(default_factory=time.time)
    steps: list[tuple[float, str, str]] = field(default_factory=list)  # (seconds in, node, description)
    result: object = None
    error: str | None = None
    finished: float | None = None

    @property
    def done(self) -> bool:
        return self.finished is not None

    @property
    def seconds(self) -> float:
        return (self.finished or time.time()) - self.started

    def record(self, node: str, update: dict) -> None:
        text = FINISHED.get(node, node)
        if node == "critic" and update.get("checks"):
            check = update["checks"][-1]
            text += ": passed" if check.passed else f": {len(check.issues)} issue(s) found"
        if node == "revise":
            text += f" (round {update.get('revisions')})"
        self.steps.append((time.time() - self.started, node, text))

    def now_working(self) -> str:
        """What the team is doing right now, from the last step that finished (the graph's order)."""
        if self.done:
            return ""
        nodes = [node for _, node, _ in self.steps]
        last = nodes[-1] if nodes else None
        if last is None:
            return "Coordinator is looking up the contract"
        if last == "coordinator" or (last in TITLES and not set(TITLES) <= set(nodes)):
            waiting = [title for node, title in TITLES.items() if node not in nodes]
            return " and ".join(waiting) + (" are" if len(waiting) > 1 else " is") + " working"
        if last in TITLES:
            return "Risk Strategist is working: worst case and the search for a lower-risk alternative"
        if last == "risk_strategist":
            return "Writer is drafting the report"
        if last in ("writer",):
            return "Critic is checking the report" + (
                " (rules first, then the LLM review: the slowest step on a local model)" if self.llm_critic else "")
        if last == "critic":
            return "The agents responsible are fixing the Critic's issues"
        if last == "revise":
            return "Writer is revising the report"
        return "Working"

    def since_last_step(self) -> float:
        return time.time() - self.started - (self.steps[-1][0] if self.steps else 0)


class Jobs:
    """Every job of this server process, shared by all browser sessions and page reloads."""

    def __init__(self):
        self.by_key: dict[tuple, Job] = {}
        self._lock = threading.Lock()

    def running(self) -> Job | None:
        return next((job for job in self.by_key.values() if not job.done), None)

    def start(self, key: tuple, label: str, llm_critic: bool, run: Callable[..., object]) -> Job:
        """Start `run(on_step=...)` in a thread; refused while another job is running."""
        with self._lock:
            if busy := self.running():
                raise RuntimeError(f"An analysis of {busy.label} is already running.")
            job = self.by_key[key] = Job(key, label, llm_critic)

        def work():
            try:
                job.result = run(on_step=job.record)
            except Exception as exc:  # noqa: BLE001 - shown on the page instead of killing the thread silently
                job.error = f"{type(exc).__name__}: {exc}"
            finally:
                job.finished = time.time()

        threading.Thread(target=work, name=f"analysis {label}", daemon=True).start()
        return job
