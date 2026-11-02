"""ToT alternative search vs the fixed-spread comparison (Checkpoint 4 evaluation).

For each evaluation contract, the same cached market data feeds four ways of finding a lower-risk
alternative, all scored on the same 100-point scale (analytics/alternatives.py):

  fixed       compare_strategies: one vertical spread, short strike ~3% beyond the bought strike
  beam_rules  ToT beam search with the rule proposer (default menu choices, no LLM)
  beam_llm    ToT beam search with the configured LLM proposing (skip with --no-llm)
  exhaustive  every path in the default menus, no beam: the best the rule menus can do

Questions: does ToT find better alternatives than the fixed spread (lower max loss, higher score,
fewer unusable picks)? Does the beam miss the exhaustive best, and how much work does it save? Does
the LLM proposer help or hurt compared with the rules? No report is written by an LLM here; the
report-quality comparison is a separate agent run (evaluate.py with use_tot).

Run with:  uv run python scripts/evaluate_tot.py            # 10 contracts, ~1 min each with the LLM
           uv run python scripts/evaluate_tot.py --no-llm   # seconds
"""

import argparse
import json
import re
import time
from datetime import datetime

from evaluate import CONTRACT_SPECS, CachingProvider, resolve

from options_trade_analyzer import config
from options_trade_analyzer.agents import tools, tot_search
from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.data import get_provider

OUT_DIR = config.PROJECT_ROOT / "docs" / "evaluation"


def fixed_spread(contract: dict, market: alt.Market, baseline: alt.Position) -> dict:
    """The compare_strategies spread, scored and pruned exactly like a ToT candidate."""
    data = json.loads(tools.compare_strategies.invoke(contract))
    if "error" in data:
        return {"strategy": None, "pruned": data["error"]}
    name = data["strategies"][1]["strategy"]
    strikes = tuple(float(s) for s in re.search(r"([\d.]+)/([\d.]+)$", name).groups())
    family = "bull call spread" if contract["option_type"] == "call" else "bear put spread"
    position = alt.build(family, strikes, contract["expiration"], market)
    if isinstance(position, str):
        return {"strategy": name, "pruned": position}
    e = alt.evaluate(position, baseline, market, contract["option_type"] == "call")
    return {"strategy": name, "expiration": contract["expiration"], "max_loss": e.max_loss,
            "score": e.score, "pruned": e.pruned}


def picked(result: dict) -> dict:
    s = result["selected"]
    if s is None:
        return {"strategy": None, "pruned": result["outcome"]}
    return {"strategy": s["strategy"], "expiration": s["expiration"], "max_loss": s["max_loss"],
            "score": s["score"], "pruned": None}


def exhaustive_best(contract: dict, market: alt.Market) -> tuple[dict, int]:
    c = contract
    candidates = sum(len(alt.expiration_choices(c["expiration"], market))
                     for family in alt.FAMILIES_FOR[c["option_type"]]
                     for _ in alt.strike_choices(family, c["strike"], c["expiration"], market, alt.DEFAULT_STRIKES_PCT))
    ranked = tot_search.exhaustive(market, c["option_type"], c["strike"], c["expiration"])
    if not ranked:
        return {"strategy": None, "pruned": "every candidate pruned"}, candidates
    e = ranked[0]
    return {"strategy": e.position.name, "expiration": e.position.expiration, "max_loss": e.max_loss,
            "score": e.score, "pruned": None}, candidates


def run_contract(contract: dict, provider, use_llm: bool) -> dict:
    c = contract
    market = alt.Market(provider, c["ticker"], config.RISK_FREE_RATE)
    baseline = alt.original(c["option_type"], c["strike"], c["expiration"], market)
    if isinstance(baseline, str):
        return {"contract": c, "error": baseline}
    earnings = provider.get_next_earnings_date(c["ticker"])
    earnings = earnings.isoformat() if earnings else None
    row = {"contract": c, "original_max_loss": alt.evaluate(baseline, baseline, market, c["option_type"] == "call").max_loss,
           "fixed": fixed_spread(c, market, baseline)}

    rules = tot_search.Search(market, c["option_type"], c["strike"], c["expiration"],
                              tot_search.RuleProposer(), earnings).run()
    row["beam_rules"] = picked(rules) | {"nodes_scored": rules["search"]["nodes_scored"],
                                          "chains_loaded": rules["search"]["option_chains_loaded"]}
    row["exhaustive"], row["exhaustive_candidates"] = exhaustive_best(c, market)
    if use_llm:
        started = time.time()
        llm = tot_search.Search(market, c["option_type"], c["strike"], c["expiration"],
                                tot_search.LLMProposer(), earnings).run()
        row["beam_llm"] = picked(llm) | {"nodes_scored": llm["search"]["nodes_scored"],
                                          "llm_proposals": llm["search"]["llm_proposals"],
                                          "llm_fallbacks": llm["search"]["llm_fallbacks"],
                                          "seconds": round(time.time() - started)}
    return row


def _cell(p: dict | None) -> str:
    if p is None:
        return "—"
    if p.get("strategy") is None or p.get("max_loss") is None:
        return f"none ({p['pruned']})"
    flag = f" · **pruned: {p['pruned']}**" if p["pruned"] else ""
    return f"{p['strategy']} {p['expiration'][5:]} · ${p['max_loss']:,.0f} · {p['score']}{flag}"


def summarize(rows: list[dict]) -> str:
    rows = [r for r in rows if "error" not in r]
    usable = lambda p: p is not None and p.get("max_loss") is not None and not p["pruned"]  # noqa: E731
    methods = ["fixed", "beam_rules"] + (["beam_llm"] if any("beam_llm" in r for r in rows) else []) + ["exhaustive"]
    n = len(rows)
    lines = [
        "# ToT alternative search vs fixed spread", "",
        f"Updated {datetime.now():%Y-%m-%d %H:%M} · {n} contracts · same cached market data for every method · "
        f"proposer model `{config.OLLAMA_MODEL if config.LLM_PROVIDER == 'ollama' else config.ANTHROPIC_MODEL}`", "",
        "Every alternative is scored on the ToT scale (100 points; pruned if a leg is illiquid, the maximum loss "
        "is not lower than the original, or the score is below 40). A *usable* alternative is one that passes "
        "those checks. Max-loss reduction is averaged over the contracts where the method found a usable one.", "",
        "| Method | Usable alternatives | Avg score (usable) | Avg max-loss reduction | Avg candidates scored |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in methods:
        ok = [r for r in rows if usable(r.get(m))]
        score = sum(r[m]["score"] for r in ok) / len(ok) if ok else 0
        cut = sum(1 - r[m]["max_loss"] / r["original_max_loss"] for r in ok) / len(ok) if ok else 0
        if m == "fixed":
            work = "1"
        else:
            key = "exhaustive_candidates" if m == "exhaustive" else None
            work = f"{sum(r[key] if key else r[m]['nodes_scored'] for r in rows if m in r) / n:.1f}"
        lines.append(f"| {m} | {len(ok)} of {n} | {score:.1f} | {cut:.0%} | {work} |")

    both = [r for r in rows if usable(r["fixed"]) and usable(r["beam_rules"])]
    better = sum(r["beam_rules"]["score"] > r["fixed"]["score"] for r in both)
    lower = sum(r["beam_rules"]["max_loss"] < r["fixed"]["max_loss"] for r in both)
    matched = sum((r["beam_rules"].get("score") == r["exhaustive"].get("score")) for r in rows)
    lines += ["", "## Head to head", "",
              f"- Fixed spread unusable (pruned or missing): {sum(not usable(r['fixed']) for r in rows)} of {n}; "
              f"ToT (rules) found a usable alternative in {sum(usable(r['beam_rules']) for r in rows)} of {n}.",
              f"- Where both were usable ({len(both)}): ToT scored higher in {better}, had a lower maximum loss in {lower}.",
              f"- Beam (rules) matched the exhaustive best score in {matched} of {n}, scoring "
              f"{sum(r['beam_rules']['nodes_scored'] for r in rows)} candidates vs "
              f"{sum(r['exhaustive_candidates'] for r in rows)} for exhaustive search."]
    llm = [r for r in rows if "beam_llm" in r]
    if llm:
        props = sum(r["beam_llm"]["llm_proposals"] for r in llm)
        falls = sum(r["beam_llm"]["llm_fallbacks"] for r in llm)
        cmp = [r for r in llm if usable(r["beam_llm"]) and usable(r["beam_rules"])]
        lines.append(f"- LLM proposer vs rules ({len(cmp)} comparable): higher score in "
                     f"{sum(r['beam_llm']['score'] > r['beam_rules']['score'] for r in cmp)}, equal in "
                     f"{sum(r['beam_llm']['score'] == r['beam_rules']['score'] for r in cmp)}, lower in "
                     f"{sum(r['beam_llm']['score'] < r['beam_rules']['score'] for r in cmp)}; "
                     f"{falls} of {props} proposals fell back to defaults; "
                     f"{sum(r['beam_llm']['seconds'] for r in llm) / len(llm):.0f} s per search on average.")

    lines += ["", "## Per contract (strategy · expiration · max loss · score)", "",
              "| Contract | Original max loss | " + " | ".join(methods) + " |",
              "| --- | --- | " + " | ".join("---" for _ in methods) + " |"]
    for r in rows:
        c = r["contract"]
        lines.append(f"| {c['ticker']} {c['strike']:g} {c['option_type']} {c['expiration']} | ${r['original_max_loss']:,.0f} | "
                     + " | ".join(_cell(r.get(m)) for m in methods) + " |")
    lines += ["", "Scores and probabilities are Black-Scholes estimates on mid-quotes, not forecasts; a lower "
              "maximum loss does not guarantee a profit. Education only."]
    return "\n".join(lines) + "\n"


def main(limit: int | None, use_llm: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    provider = CachingProvider(get_provider(config.DATA_PROVIDER))
    tools.provider = provider  # compare_strategies reads the same cached data
    rows = []
    for spec in CONTRACT_SPECS[:limit]:
        try:
            contract = resolve(provider, *spec)
            print(f"{contract['ticker']} {contract['strike']:g} {contract['option_type']} {contract['expiration']} ...", flush=True)
            rows.append(run_contract(contract, provider, use_llm))
        except Exception as exc:  # one bad contract (e.g. missing data) must not stop the run
            print(f"  failed: {exc}", flush=True)
            continue
        (OUT_DIR / "tot_results.json").write_text(json.dumps(rows, indent=1, default=str))
        (OUT_DIR / "tot_summary.md").write_text(summarize(rows))
    print(f"Done. Summary: {OUT_DIR / 'tot_summary.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="only the first N contracts")
    parser.add_argument("--no-llm", action="store_true", help="skip the LLM-proposer search")
    args = parser.parse_args()
    main(args.limit, not args.no_llm)
