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

Risk-adjusted comparison (Checkpoint 4 feedback): is a pick better, or only a smaller maximum loss?
The original contract and every method's pick are also measured with analytics/risk_metrics.py:
expected profit and chance of profit under Black-Scholes and under the stock's own past 2 years of
moves, bid-ask cost, value change under implied-volatility shifts, and maximum gain per dollar risked.

Run with:  uv run python scripts/evaluate_tot.py            # 10 contracts, ~1 min each with the LLM
           uv run python scripts/evaluate_tot.py --no-llm   # seconds
           --out NAME writes tot_results_NAME.json / tot_summary_NAME.md (keeps earlier results)
           --before-after also scores the same cached data the Checkpoint 4 way (no lottery-ticket floor,
                          risk at mid-quotes) into tot_*_NAME_checkpoint4.*
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
from options_trade_analyzer.analytics import risk_metrics
from options_trade_analyzer.data import get_provider

OUT_DIR = config.PROJECT_ROOT / "docs" / "evaluation"
METHODS = ["fixed", "beam_rules", "beam_llm", "exhaustive"]
HISTORY = "2y"


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


def position_of(pick: dict | None, market: alt.Market) -> alt.Position | None:
    """Rebuild a picked position from its name, e.g. "bull put spread 345/340" on its expiration."""
    if not pick or pick.get("strategy") is None or pick.get("expiration") is None:
        return None
    family, strikes = pick["strategy"].rsplit(" ", 1)
    position = alt.build(family, tuple(float(k) for k in strikes.split("/")), pick["expiration"], market)
    return None if isinstance(position, str) else position


def risk_adjusted(row: dict, baseline: alt.Position, market: alt.Market, closes) -> dict:
    risk = {"original": risk_metrics.measure(baseline, market, closes)}
    for m in METHODS:
        position = position_of(row.get(m), market)
        if position is not None:
            risk[m] = risk_metrics.measure(position, market, closes)
    return risk


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
    closes = provider.get_price_history(c["ticker"], HISTORY)["Close"]
    row["risk"] = risk_adjusted(row, baseline, market, closes)
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
    if any("risk" in r for r in rows):
        lines += _risk_section([r for r in rows if "risk" in r], methods, usable)
    lines += ["", "Scores and probabilities are Black-Scholes estimates on mid-quotes, not forecasts; a lower "
              "maximum loss does not guarantee a profit. Education only."]
    return "\n".join(lines) + "\n"


def _per_100(value: float, loss: float) -> float:
    return value / loss * 100 if loss else 0.0


def _usd(value: float, digits: int = 0) -> str:
    return f"{'-' if value < 0 else '+'}${abs(value):,.{digits}f}"


def _risk_section(rows: list[dict], methods: list[str], usable) -> list[str]:
    """Risk-adjusted averages per method, each figure per $100 of that position's own maximum loss."""
    base_set = [r for r in rows if usable(r["beam_rules"])]
    groups = [("original", base_set)] + [(m, [r for r in rows if m in r["risk"] and usable(r.get(m))])
                                         for m in methods]
    lines = ["", "## Risk-adjusted comparison", "",
             "Is the pick better, or only a smaller maximum loss? Each figure is per $100 of that position's own "
             "maximum loss, so a $300 spread and an $800 call compare fairly. *Past moves*: every overlapping "
             f"window of the stock's last {HISTORY} with the same number of trading days to expiration, applied to "
             "today's price. *Black-Scholes*: the distribution the option prices imply (drift = risk-free rate, the "
             "legs' average implied volatility). Only its chance of profit is shown: its expected profit is about zero "
             "by construction, and what remains measures how one shared volatility misprices legs with different "
             "implied volatilities, not an edge. Bid-ask is the round trip (open and close) versus the mid-quote. "
             "`original` is averaged over the contracts where ToT (rules) found a usable alternative; each method "
             "over its own usable picks.", "",
             "| Position | Contracts | Max gain per $1 risked | Expected P/L, past moves | Chance of profit, past moves "
             "| Chance of profit, Black-Scholes | Bid-ask round trip | IV −40% | IV +20% |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, rs in groups:
        ms = [r["risk"][name] for r in rs if name in r["risk"]]
        ms = [x for x in ms if "error" not in x["historical"]]
        if not ms:
            continue
        avg = lambda f: sum(f(x) for x in ms) / len(ms)  # noqa: E731
        finite = [x["reward_to_risk"] for x in ms if x["reward_to_risk"] is not None]
        gain = f"{sum(finite) / len(finite):.2f}" if len(finite) == len(ms) else "unlimited"
        lines.append(
            f"| {name} | {len(ms)} | {gain} "
            f"| {_usd(avg(lambda x: _per_100(x['historical']['expected_pnl'], x['max_loss'])), 1)} "
            f"| {avg(lambda x: x['historical']['chance_of_profit_pct']):.0f}% "
            f"| {avg(lambda x: x['risk_neutral']['chance_of_profit_pct']):.0f}% "
            f"| ${avg(lambda x: _per_100(x['spread_cost']['round_trip'], x['max_loss'])):.1f} "
            f"| {_usd(avg(lambda x: _per_100(x['iv_change']['-40%'], x['max_loss'])), 1)} "
            f"| {_usd(avg(lambda x: _per_100(x['iv_change']['+20%'], x['max_loss'])), 1)} |")

    lines += ["", "### Per contract (dollars per one set of contracts)", "",
              "| Contract | Position | Picked by | Max loss | Max gain | Expected P/L, past moves | Chance, past moves "
              "| Chance, Black-Scholes | Bid-ask round trip | IV −40% | IV +20% |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        c = r["contract"]
        seen: dict[tuple, list[str]] = {}
        for name in ["original"] + methods:
            x = r["risk"].get(name)
            if x:
                seen.setdefault((x["strategy"], x["expiration"]), []).append(name)
        for (strategy, expiration), names in seen.items():
            x = r["risk"][names[0]]
            h = x["historical"]
            gain = x["max_gain"] if isinstance(x["max_gain"], str) else f"${x['max_gain']:,.0f}"
            past = ("n/a", "n/a") if "error" in h else (_usd(h['expected_pnl']), f"{h['chance_of_profit_pct']:.0f}%")
            label = ", ".join(n for n in names if n == "original" or usable(r.get(n))) or \
                ", ".join(f"{n} (pruned)" for n in names)
            lines.append(f"| {c['ticker']} {c['strike']:g} {c['option_type']} {c['expiration']} | {strategy} {expiration[5:]} "
                         f"| {label} | ${x['max_loss']:,.0f} | {gain} | {past[0]} | {past[1]} "
                         f"| {x['risk_neutral']['chance_of_profit_pct']:.0f}% | ${x['spread_cost']['round_trip']:,.0f} "
                         f"| {_usd(x['iv_change']['-40%'])} | {_usd(x['iv_change']['+20%'])} |")
    return lines


def use_checkpoint4_score(on: bool) -> None:
    """Checkpoint 4 scoring: no chance-of-profit floor, risk reduction at mid-quotes."""
    alt.MIN_CHANCE, alt.COUNT_BID_ASK = (0.0, False) if on else (CURRENT_MIN_CHANCE, True)


CURRENT_MIN_CHANCE = alt.MIN_CHANCE


def main(limit: int | None, use_llm: bool, out: str | None = None, before_after: bool = False) -> None:
    provider = CachingProvider(get_provider(config.DATA_PROVIDER))
    tools.provider = provider  # compare_strategies reads the same cached data
    if before_after:  # same cached market data for both scorings
        use_checkpoint4_score(True)
        run_all(limit, use_llm, f"{out or 'run'}_checkpoint4", provider)
        use_checkpoint4_score(False)
    run_all(limit, use_llm, out, provider)


def run_all(limit: int | None, use_llm: bool, out: str | None, provider) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{out}" if out else ""
    rows = []
    for spec in CONTRACT_SPECS[:limit]:
        try:
            contract = resolve(provider, *spec)
            print(f"{contract['ticker']} {contract['strike']:g} {contract['option_type']} {contract['expiration']} ...", flush=True)
            rows.append(run_contract(contract, provider, use_llm))
        except Exception as exc:  # one bad contract (e.g. missing data) must not stop the run
            print(f"  failed: {exc}", flush=True)
            continue
        (OUT_DIR / f"tot_results{suffix}.json").write_text(json.dumps(rows, indent=1, default=str))
        (OUT_DIR / f"tot_summary{suffix}.md").write_text(summarize(rows))
    print(f"Done. Summary: {OUT_DIR / f'tot_summary{suffix}.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="only the first N contracts")
    parser.add_argument("--no-llm", action="store_true", help="skip the LLM-proposer search")
    parser.add_argument("--out", default=None, help="name for separate results/summary files")
    parser.add_argument("--before-after", action="store_true", help="also score with the Checkpoint 4 rules")
    args = parser.parse_args()
    main(args.limit, not args.no_llm, args.out, args.before_after)
