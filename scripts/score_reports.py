"""Score evaluation reports against answer keys built from the snapshot (report quality, not just errors).

Builds one answer key per snapshot contract (answer_keys.py), saves them to
data/answer_keys/<snapshot>.json so the expectations can be read and checked, then scores every report in
docs/evaluation/results_<NAME>.json and writes docs/evaluation/quality_<NAME>.md.

Run with:  DATA_PROVIDER=snapshot SNAPSHOT_PATH=data/snapshots/2026-11-06.json.gz \\
           uv run python scripts/score_reports.py compare
No LLM and no network: seconds.
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from options_trade_analyzer import answer_keys as ak
from options_trade_analyzer import config
from options_trade_analyzer.agents import tools
from options_trade_analyzer.data import get_provider

EVAL_DIR = config.PROJECT_ROOT / "docs" / "evaluation"
KEY_DIR = config.PROJECT_ROOT / "data" / "answer_keys"


def contract_id(contract: dict) -> str:
    return json.dumps(contract, sort_keys=True)


def build_keys(provider) -> dict[str, dict]:
    keys = {contract_id(c): ak.build_key(provider, c) for c in provider.contracts}
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    path = KEY_DIR / (Path(config.SNAPSHOT_PATH).name.removesuffix(".json.gz") + ".json")
    path.write_text(json.dumps(list(keys.values()), indent=1))
    print(f"Answer keys: {path.relative_to(config.PROJECT_ROOT)} ({len(keys)} contracts)")
    return keys


def summarize(name: str, scored: list[dict], descriptions: dict[str, str]) -> str:
    setups = list(dict.fromkeys(s["setup"] for s in scored))
    lines = [f"# Report quality against answer keys: {name}", "",
             f"Updated {datetime.now():%Y-%m-%d %H:%M} · snapshot `{config.SNAPSHOT_PATH}` · {len(scored)} reports", "",
             "Each report is checked against its contract's answer key: facts a correct report must state, and "
             "mistakes it must not make (built from the snapshot with the project's tools; plain text and number "
             "matching, so spot-check unusual wordings).", "",
             "| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |",
             "| --- | --- | --- | --- | --- | --- |"]
    for setup in setups:
        rs = [s for s in scored if s["setup"] == setup]
        met, total = sum(s["must_met"] for s in rs), sum(s["must_total"] for s in rs)
        lines.append(f"| {setup} | {len(rs)} | {met} of {total} ({met / total:.0%}) "
                     f"| {sum(s['must_met'] == s['must_total'] for s in rs)} | {sum(s['mistakes'] for s in rs)} "
                     f"| {sum(s['mistakes'] == 0 for s in rs)} |")
    lines += ["", "## Most often missed or wrong", "", "| Setup | Item | Reports |", "| --- | --- | --- |"]
    for setup in setups:
        counts = Counter(i for s in scored if s["setup"] == setup for i in s["missing"] + s["made"])
        for item, n in counts.most_common(5):
            lines.append(f"| {setup} | {descriptions[item]} | {n} |")
    lines += ["", "## Per report", "", "| Contract | Setup | Facts met | Missing | Mistakes |", "| --- | --- | --- | --- | --- |"]
    for s in scored:
        c = s["contract"]
        lines.append(f"| {c['ticker']} {c['strike']:g} {c['option_type']} {c['expiration']} | {s['setup']} "
                     f"| {s['must_met']} of {s['must_total']} | {', '.join(s['missing']) or '—'} "
                     f"| {', '.join(s['made']) or '—'} |")
    return "\n".join(lines) + "\n"


def main(name: str) -> None:
    if config.DATA_PROVIDER != "snapshot":
        raise SystemExit("Set DATA_PROVIDER=snapshot and SNAPSHOT_PATH: answer keys come from the recorded data.")
    provider = get_provider("snapshot")
    tools.provider = provider
    keys = build_keys(provider)
    descriptions = {i["id"]: ak.GENERIC.get(i["id"], i["description"]) for k in keys.values() for i in k["items"]}
    runs = json.loads((EVAL_DIR / f"results_{name}.json").read_text())
    scored, skipped = [], 0
    for run in runs:
        key = keys.get(contract_id(run["contract"]))
        if key is None:  # a contract that is not in this snapshot
            skipped += 1
            continue
        scored.append({"contract": run["contract"], "setup": run["setup"],
                       **ak.score(run["report"], key, run["trace"])})
    out = EVAL_DIR / f"quality_{name}.md"
    out.write_text(summarize(name, scored, descriptions))
    print(f"Scored {len(scored)} reports ({skipped} skipped: contract not in the snapshot) -> "
          f"{out.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="the NAME in docs/evaluation/results_NAME.json, e.g. compare")
    main(parser.parse_args().name)
