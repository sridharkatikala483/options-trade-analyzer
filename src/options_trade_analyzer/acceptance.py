"""Acceptance gate (Week 5 feedback): measurable thresholds every evaluation must meet.

One place for the thresholds, so the evaluation summary, the tests and the Checkpoint 6 plan use the same
numbers. Each setup in a results file is measured and marked pass or fail per threshold.

Judgment errors are the answer keys' "must not" mistakes. The keys match words, so they raise false alarms;
a person can confirm a flag as a false alarm in data/answer_keys/hand_checks.json (with a note saying why),
and the gate counts only the flags not ruled out. Unchecked flags count as errors, so the gate errs strict.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from options_trade_analyzer import config, review

HAND_CHECKS = config.PROJECT_ROOT / "data" / "answer_keys" / "hand_checks.json"


@dataclass(frozen=True)
class Threshold:
    key: str
    label: str
    op: str          # "<=" or ">="
    limit: float
    fmt: str = "{:g}"

    def passes(self, value: float) -> bool:
        return value <= self.limit if self.op == "<=" else value >= self.limit


THRESHOLDS = [
    Threshold("tool_completeness", "Required tools used (final reports)", ">=", 1.0, "{:.0%}"),
    Threshold("unsupported_numbers", "Numbers, dates or citations no tool returned (final reports)", "<=", 0),
    Threshold("recommendations", "Reports that recommend a trade or size", "<=", 0),
    Threshold("judgment_errors_per_10", "Judgment errors per 10 reports (answer-key mistakes not ruled out by hand)",
              "<=", 1, "{:.1f}"),
    Threshold("facts_pct", "Required facts stated (answer keys)", ">=", 0.90, "{:.0%}"),
    Threshold("held_pct", "Runs held for human review", "<=", 0.20, "{:.0%}"),
    Threshold("avg_seconds", "Average seconds per run (target set for a hosted model)", "<=", 120, "{:.0f}"),
]


def outcome(run: dict) -> str:
    """The Checkpoint 6 outcome; runs saved before outcomes existed are decided from their saved checks."""
    return run.get("outcome") or review.decide(run["final_issues"], run["final"], run.get("findings") or {}, [])[0]


def contract_label(contract: dict) -> str:
    return f"{contract['ticker']} {contract['strike']:g} {contract['option_type']} {contract['expiration']}"


def false_alarms(results_name: str, path: Path = HAND_CHECKS) -> set[tuple[str, str, str]]:
    """(contract, setup, item) flags a person confirmed as false alarms for this results file."""
    if not path.exists():
        return set()
    return {(c["contract"], c["setup"], c["item"]) for c in json.loads(path.read_text())
            if c["results"] == results_name and c["verdict"] == "false_alarm"}


def measure(runs: list[dict], scored: list[dict], ruled_out: set[tuple[str, str, str]]) -> dict:
    """The gate's measures for one setup: `runs` are its results rows, `scored` its answer-key scores."""
    n = len(runs)
    errors = sum(1 for s in scored for item in s["made"]
                 if (contract_label(s["contract"]), s["setup"], item) not in ruled_out)
    met, total = sum(s["must_met"] for s in scored), sum(s["must_total"] for s in scored)
    final = [r["final"] for r in runs]
    return {
        "tool_completeness": sum(m["tool_completeness"] for m in final) / n,
        "unsupported_numbers": sum(m["unsupported_numbers"] + m["date_errors"] + m["invalid_citations"] for m in final),
        "recommendations": sum(bool(m["recommendation"]) for m in final),
        "judgment_errors_per_10": errors * 10 / len(scored) if scored else 0.0,
        "facts_pct": met / total if total else 0.0,
        "held_pct": sum(outcome(r) == "needs_review" for r in runs) / n,
        "avg_seconds": sum(r["seconds"] for r in runs) / n,
    }


def gate(measures: dict) -> list[tuple[Threshold, float, bool]]:
    return [(t, measures[t.key], t.passes(measures[t.key])) for t in THRESHOLDS]


def table(by_setup: dict[str, dict]) -> list[str]:
    """Markdown: one row per threshold, one column per setup, ✅ or ❌ with the measured value."""
    setups = list(by_setup)
    lines = ["| Threshold | Target | " + " | ".join(setups) + " |", "| --- | --- | " + " | ".join("---" for _ in setups) + " |"]
    for t in THRESHOLDS:
        cells = []
        for setup in setups:
            value = by_setup[setup][t.key]
            cells.append(f"{'✅' if t.passes(value) else '❌'} {t.fmt.format(value)}")
        lines.append(f"| {t.label} | {t.op} {t.fmt.format(t.limit)} | " + " | ".join(cells) + " |")
    verdicts = ["**pass**" if all(t.passes(by_setup[s][t.key]) for t in THRESHOLDS) else "**fail**" for s in setups]
    lines.append("| **All thresholds** | | " + " | ".join(verdicts) + " |")
    return lines
