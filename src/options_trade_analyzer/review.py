"""Checkpoint 6 outcomes, run log and human review queue.

Code, never the model, decides each run's outcome from the check results:
  shown               every check passed, no input risk flags
  shown_with_warning  every check passed, but the contract itself is risky (input_risk flags)
  needs_review        a check still fails after the revision rounds, the LLM Critic's reply was unreadable,
                      a specialist failed, market data was missing or a data source failed, a headline
                      was withheld as a possible injection, or the run stopped with an error
  refused             the request could not be analyzed (no such contract)

Every dashboard run is appended to data/runs/runs.jsonl (gitignored) with its request, outcome, checks,
report and full trace. A reviewer's decision (approved / edited / rejected) is appended to reviews.jsonl,
never written over the run, so the log stays an audit trail. Timestamps use clock.wall_now(): a snapshot
replay freezes the market clock, not the time a person ran or reviewed something.

The queue is sorted by priority (critical, high, medium, low): the most dangerous problem in a held run
decides its level, so a made-up maximum loss is reviewed before a missing implied volatility.
"""

import json
import re
import threading
import uuid
from pathlib import Path
from typing import Callable, Literal

from options_trade_analyzer import clock, config

Outcome = Literal["shown", "shown_with_warning", "needs_review", "refused"]
Decision = Literal["approved", "edited", "rejected"]
LOG_DIR = config.PROJECT_ROOT / "data" / "runs"
_lock = threading.Lock()
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")


def decide(issues: list[str], metrics: dict, findings: dict, flags: list, error: str | None = None,
           invalid_request: str | None = None, withheld: int = 0,
           failed_sources: list[str] | None = None) -> tuple[Outcome, list[str]]:
    """The outcome and the reasons a reviewer reads, from a finished run's checks."""
    if invalid_request:
        return "refused", [f"The request could not be analyzed: {invalid_request}"]
    reasons = []
    if error:
        reasons.append(f"The run stopped with an error: {error}")
    for name, text in findings.items():
        if str(text).startswith("FAILED"):
            reasons.append(f"The {name.replace('_', ' ')} failed, so part of the analysis is missing.")
    if issues:
        reasons.append(f"{len(issues)} check(s) still fail after the revision rounds.")
    for flag in flags:
        if flag.get("id") == "missing_data":
            reasons.append(f"Market data was missing ({'; '.join(flag['missing'])}), so the analysis is low confidence.")
    if failed_sources:
        reasons.append(f"A data source failed and was not recovered ({', '.join(failed_sources)}), so part of the "
                       "analysis is missing.")
    if withheld:
        reasons.append(f"{withheld} headline(s) read like instructions to an AI and were withheld; check that "
                       "the report was not steered.")
    if metrics.get("llm_critic_error"):
        reasons.append("The LLM Critic's reply could not be read, so the judgment review did not happen.")
    if reasons:
        return "needs_review", reasons
    return ("shown_with_warning", [f["message"] for f in flags]) if flags else ("shown", [])


def decide_result(result, error: str | None = None) -> tuple[Outcome, list[str]]:
    """decide() for an AnalysisResult (None when the run raised)."""
    if result is None:
        return decide([], {}, {}, [], error=error or "no result")
    v = result.verification
    return decide(v.issues, v.metrics, result.findings, result.flags, error, result.invalid_request,
                  withheld_headlines(result.trace), failed_sources(result.trace))


def failed_sources(trace: list[dict]) -> list[str]:
    """Tools whose data source failed in this run and never succeeded on a later call."""
    last: dict[str, bool] = {}
    for step in trace:
        if step["step"] == "Observation" and step.get("tool"):
            try:
                error = str(json.loads(step["text"]).get("error", ""))
            except (json.JSONDecodeError, AttributeError):
                continue
            last[step["tool"]] = error.startswith("data unavailable")
    return [tool for tool, failed in last.items() if failed]


def withheld_headlines(trace: list[dict]) -> int:
    """Headlines the injection monitor withheld in this run (largest count of any news search)."""
    counts = [0]
    for step in trace:
        if step["step"] == "Observation" and step.get("tool") == "search_recent_news":
            try:
                counts.append(len(json.loads(step["text"]).get("withheld", [])))
            except (json.JSONDecodeError, AttributeError):
                pass
    return max(counts)


# --- the log ---

def _append(name: str, record: dict, log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    with _lock, open(log_dir / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _read(name: str, log_dir: Path) -> list[dict]:
    path = log_dir / name
    if not path.exists():
        return []
    with _lock:
        lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def run_and_log(request: dict, setup: dict, run: Callable[[], object], log_dir: Path = LOG_DIR):
    """Run an analysis, decide its outcome, append it to the log and return the result (with outcome and
    run id set). An exception is logged as needs_review and raised again for the caller to show."""
    run_id, started = uuid.uuid4().hex[:12], clock.wall_now()
    result, error = None, None
    try:
        result = run()
    except Exception as exc:  # noqa: BLE001 - logged, then re-raised
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        outcome, reasons = decide_result(result, error)
        record = {"run_id": run_id, "started": started.isoformat(), "finished": clock.wall_now().isoformat(),
                  "request": request, "setup": setup,
                  "model": config.OLLAMA_MODEL if config.LLM_PROVIDER == "ollama" else config.ANTHROPIC_MODEL,
                  "data": config.DATA_PROVIDER + (f" ({config.SNAPSHOT_PATH})" if config.DATA_PROVIDER == "snapshot" else ""),
                  "outcome": outcome, "reasons": reasons, "error": error}
        if result is not None:
            result.outcome, result.reasons, result.run_id = outcome, reasons, run_id
            record |= {"flags": result.flags, "issues": result.verification.issues,
                       "checks": result.verification.metrics, "first_draft": result.first_draft_verification.metrics,
                       "revisions": result.revisions, "tokens": result.tokens, "report": result.report,
                       "findings": result.findings, "routing": result.routing, "trace": result.trace}
        _append("runs.jsonl", record, log_dir)
    return result


def log_review(run_id: str, decision: Decision, note: str = "", report: str | None = None,
               log_dir: Path = LOG_DIR) -> dict:
    """Record a reviewer's decision; an edit keeps the reviewer's version of the report."""
    if decision == "edited" and not (report or "").strip():
        raise ValueError("an edited decision needs the edited report")
    record = {"run_id": run_id, "decision": decision, "note": note.strip(), "at": clock.wall_now().isoformat()}
    if decision == "edited":
        record["report"] = report
    _append("reviews.jsonl", record, log_dir)
    return record


def runs(log_dir: Path = LOG_DIR) -> list[dict]:
    """Every logged run, newest first, each with its latest review (or None)."""
    reviews = {}
    for r in _read("reviews.jsonl", log_dir):
        reviews[r["run_id"]] = r  # later decisions replace earlier ones
    return [run | {"review": reviews.get(run["run_id"])} for run in reversed(_read("runs.jsonl", log_dir))]


# --- review priority (Checkpoint 6 feedback: the most dangerous errors first) ---

LEVELS = ("low", "medium", "high", "critical")
KEY_NUMBER = re.compile(r"\b(max(imum)?\s+(loss|gain|profit)|break[- ]?even|premium|cost|debit|credit|chance|"
                        r"probability|loses?|lose)\b", re.I)
ISSUE_LEVELS = [  # verifier issue opening -> level; the first match wins, anything unknown counts as high
    (re.compile(r"^Report contains a recommendation"), "critical"),
    (re.compile(r" was called with (strike|expiration) "), "critical"),
    (re.compile(r"^(Number not found|Date not returned)"), "high"),
    (re.compile(r"^(Overconfident wording|The alternative's trade-off|Missing statement|Report describes liquidity)"),
     "high"),
    (re.compile(r"^(Required tool not called|Citation|The report talks about its own revision)"), "medium"),
]
REASON_LEVELS = [  # decide() reason opening -> level; "N check(s) still fail" is covered by the issues
    (re.compile(r"headline\(s\) read like instructions"), "critical"),
    (re.compile(r"^The run stopped with an error|^The .+ failed, so part of the analysis is missing"), "high"),
    (re.compile(r"^A data source failed|^The LLM Critic's reply"), "medium"),
    (re.compile(r"^Market data was missing"), "low"),
]


def _issue_level(issue: str, report: str) -> str:
    if issue.startswith("Number not found"):
        token = issue.split(": ", 1)[-1].removesuffix(".")
        sentences = [s for s in SENTENCE.split(report) if token in s]
        if any(KEY_NUMBER.search(s) for s in sentences):
            return "critical"  # a made-up maximum loss, breakeven, cost or chance misleads the most
    return next((level for pattern, level in ISSUE_LEVELS if pattern.search(issue)), "high")


def priority(record: dict) -> dict:
    """How urgently a held run needs a person: its most dangerous problem decides the level."""
    found = [(_issue_level(i, record.get("report") or ""), i) for i in record.get("issues") or []]
    found += [(level, r) for r in record.get("reasons") or []
              for pattern, level in REASON_LEVELS if pattern.search(r)]
    if not found:
        return {"level": "high", "rank": LEVELS.index("high"), "why": "held without a recorded reason"}
    level, why = max(found, key=lambda f: LEVELS.index(f[0]))
    return {"level": level, "rank": LEVELS.index(level), "why": why,
            "count": sum(f[0] == level for f in found)}


def queue(log_dir: Path = LOG_DIR) -> list[dict]:
    """Runs held for review that nobody has decided yet: most dangerous first, oldest first within a level."""
    pending = [r | {"priority": priority(r)} for r in reversed(runs(log_dir))
               if r["outcome"] == "needs_review" and r["review"] is None]
    return sorted(pending, key=lambda r: -r["priority"]["rank"])  # stable: keeps oldest first within a level


def escalation_rate(records: list[dict]) -> float | None:
    """Share of runs held for review (the Checkpoint 6 target is 20% or less)."""
    return sum(r["outcome"] == "needs_review" for r in records) / len(records) if records else None
