"""Evaluation harness (Checkpoint 3 feedback): does retrieval improve quality, and do the validation
checks reduce errors? Runs the Options agent on several contracts in three setups and scores every
final report with the verifier.

Setups
  no_retrieval        core tools only, no verification loop
  retrieval           + knowledge and news retrieval, no verification loop
  retrieval_verified  + retrieval, with the completeness/verification loop (max 2 revisions)

Metrics per run: tool-use completeness, unsupported numbers, date errors, liquidity contradictions
(general guidance misapplied to this contract), citation accuracy, recommendations, revisions,
runtime and tokens. Market data and headlines are cached per contract so all setups see the same
inputs. Results are saved after every run, so an interrupted run resumes where it stopped.

Run with:  uv run python scripts/evaluate.py                # all contracts, all setups
           uv run python scripts/evaluate.py --limit 2      # quick check
"""

import argparse
import functools
import json
import time
from dataclasses import asdict
from datetime import date, datetime

from options_trade_analyzer import config
from options_trade_analyzer.agents import tools
from options_trade_analyzer.agents.options_agent import analyze_contract
from options_trade_analyzer.data import get_provider
from options_trade_analyzer.retrieval import news as news_retrieval

OUT_DIR = config.PROJECT_ROOT / "docs" / "evaluation"

# Varied on purpose: calls and puts, near and far expiries, at/out of the money, earnings before
# expiry or not, a broad ETF, a low-volatility stock and a likely illiquid far-out-of-the-money contract.
CONTRACT_SPECS = [
    ("AAPL", "call", 0.00, 10), ("AAPL", "put", 0.00, 10), ("MSFT", "call", 0.05, 30),
    ("NVDA", "call", 0.00, 10), ("TSLA", "put", 0.05, 10), ("KO", "call", 0.00, 30),
    ("AMD", "call", 0.10, 30), ("SPY", "call", 0.00, 7), ("F", "call", 0.15, 45), ("JPM", "put", 0.05, 30),
]
SETUPS = {
    "no_retrieval": {"use_retrieval": False, "verify_report": False},
    "retrieval": {"use_retrieval": True, "verify_report": False},
    "retrieval_verified": {"use_retrieval": True, "verify_report": True},
}
METRICS = ["tool_completeness", "unsupported_numbers", "date_errors", "liquidity_contradictions",
           "invalid_citations", "citations", "recommendation"]


class CachingProvider:
    """Memoizes every provider call so all setups for a contract see identical market data."""

    def __init__(self, inner):
        self._inner = inner
        self._cached = {}

    def __getattr__(self, name):
        if name not in self._cached:
            self._cached[name] = functools.lru_cache(maxsize=None)(getattr(self._inner, name))
        return self._cached[name]


def resolve(provider, ticker: str, option_type: str, otm: float, days: int) -> dict:
    """Turn a spec into a listed contract: first expiry at least `days` out, strike nearest the target."""
    spot = provider.get_quote(ticker)
    expiry = next(e for e in provider.get_expirations(ticker)
                  if (date.fromisoformat(e) - date.today()).days >= days)
    target = spot * (1 + otm) if option_type == "call" else spot * (1 - otm)
    chain = provider.get_option_chain(ticker, expiry)[f"{option_type}s"]
    strike = float(min(chain["strike"], key=lambda s: abs(s - target)))
    return {"ticker": ticker, "option_type": option_type, "strike": strike, "expiration": expiry}


def run_one(contract: dict, setup: str) -> dict:
    started = time.time()
    result = analyze_contract(**contract, **SETUPS[setup])
    return {
        "contract": contract,
        "setup": setup,
        "seconds": round(time.time() - started),
        "revisions": result.revisions,
        "tokens": result.tokens,
        "final": result.verification.metrics,
        "final_issues": result.verification.issues,
        "first_draft": result.first_draft_verification.metrics,
        "report": result.report,
        "trace": result.trace,
    }


def summarize(runs: list[dict]) -> str:
    lines = [
        "# Evaluation results", "",
        f"Updated {datetime.now():%Y-%m-%d %H:%M} · model `{config.OLLAMA_MODEL if config.LLM_PROVIDER == 'ollama' else config.ANTHROPIC_MODEL}`"
        f" · {len({json.dumps(r['contract']) for r in runs})} contracts · {len(runs)} runs", "",
        "Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified",
        "setup is also *revised* by the same verifier, so its final scores show what the loop achieves;",
        "its first-draft scores show the agent before verification.", "",
        "| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions "
        "| Citation accuracy | Recommendations | Avg revisions | Avg seconds | Avg tokens (in/out) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for setup in SETUPS:
        for stage in (["first_draft", "final"] if setup == "retrieval_verified" else ["final"]):
            rs = [r for r in runs if r["setup"] == setup]
            if not rs:
                continue
            m = [r[stage] for r in rs]
            cites = sum(x["citations"] for x in m)
            bad = sum(x["invalid_citations"] for x in m)
            label = setup if setup != "retrieval_verified" else f"{setup} ({stage.replace('_', ' ')})"
            lines.append(
                f"| {label} | {len(rs)} | {sum(x['tool_completeness'] for x in m) / len(m):.0%} "
                f"| {sum(x['unsupported_numbers'] for x in m)} | {sum(x['date_errors'] for x in m)} "
                f"| {sum(x['liquidity_contradictions'] for x in m)} "
                f"| {f'{1 - bad / cites:.0%} of {cites}' if cites else 'n/a'} "
                f"| {sum(bool(x['recommendation']) for x in m)} "
                f"| {sum(r['revisions'] for r in rs) / len(rs):.1f} | {sum(r['seconds'] for r in rs) / len(rs):.0f} "
                f"| {sum(r['tokens']['input'] for r in rs) // len(rs)} / {sum(r['tokens']['output'] for r in rs) // len(rs)} |")
    lines += ["", "## Per run", "", "| Contract | Setup | Completeness | Unsupported numbers | Date errors "
              "| Liquidity contradictions | Invalid citations | Revisions |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in runs:
        c, m = r["contract"], r["final"]
        lines.append(f"| {c['ticker']} {c['strike']:g} {c['option_type']} {c['expiration']} | {r['setup']} "
                     f"| {m['tool_completeness']:.0%} | {m['unsupported_numbers']} | {m['date_errors']} "
                     f"| {m['liquidity_contradictions']} | {m['invalid_citations']} of {m['citations']} | {r['revisions']} |")
    return "\n".join(lines) + "\n"


def main(limit: int | None, setups: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results_file = OUT_DIR / "results.json"
    runs = json.loads(results_file.read_text()) if results_file.exists() else []
    done = {(json.dumps(r["contract"], sort_keys=True), r["setup"]) for r in runs}

    provider = CachingProvider(get_provider(config.DATA_PROVIDER))
    tools.provider = provider  # every tool now reads the cached data
    news_retrieval.fetch_headlines = functools.lru_cache(maxsize=None)(news_retrieval.fetch_headlines)

    # On resume, reuse contracts already started: resolving again on a later day can pick a new expiry.
    started = {(r["contract"]["ticker"], r["contract"]["option_type"]): r["contract"] for r in runs}
    contracts = [started.get(spec[:2]) or resolve(provider, *spec) for spec in CONTRACT_SPECS[:limit]]
    for contract in contracts:
        for setup in setups:
            key = (json.dumps(contract, sort_keys=True), setup)
            if key in done:
                continue
            print(f"Running {contract['ticker']} {contract['strike']:g} {contract['option_type']} "
                  f"{contract['expiration']} [{setup}] ...", flush=True)
            try:
                runs.append(run_one(contract, setup))
            except Exception as exc:  # one failed run must not stop an overnight evaluation
                print(f"  failed: {exc}", flush=True)
                continue
            results_file.write_text(json.dumps(runs, indent=1, default=str))
            (OUT_DIR / "summary.md").write_text(summarize(runs))
    print(f"Done. Summary: {OUT_DIR / 'summary.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="only the first N contracts")
    parser.add_argument("--setups", default=",".join(SETUPS), help="comma-separated subset of setups")
    args = parser.parse_args()
    main(args.limit, args.setups.split(","))
