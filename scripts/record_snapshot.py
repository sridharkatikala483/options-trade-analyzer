"""Record a market-data snapshot of the evaluation contracts, for repeatable runs.

Fetches, once and live, everything the agents and evaluation scripts read for each contract in
evaluate.CONTRACT_SPECS: quote, expirations, the option chains the alternative search can visit,
earnings and ex-dividend dates, 6-month and 2-year price history, and recent headlines. Saves it to
data/snapshots/<date>.json.gz. Replay it by setting in .env:

    DATA_PROVIDER=snapshot
    SNAPSHOT_PATH=data/snapshots/<date>.json.gz

Run with:  uv run python scripts/record_snapshot.py            # a few minutes, needs the internet
           uv run python scripts/record_snapshot.py --specs scenarios   # the scenario set -> <date>-scenarios
"""

import argparse

from evaluate import SPEC_SETS, resolve

from options_trade_analyzer import clock, config
from options_trade_analyzer.agents import tools
from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.data import YFinanceProvider
from options_trade_analyzer.data.snapshot import RecordingProvider, SnapshotProvider

OUT_DIR = config.PROJECT_ROOT / "data" / "snapshots"
HISTORY_PERIODS = ("6mo", "2y")  # get_price_trend, and the risk-adjusted measures in evaluate_tot.py


def record_contract(recorder: RecordingProvider, spec: tuple) -> dict:
    contract = resolve(recorder, *spec)
    ticker = contract["ticker"]
    tools.get_option_contract.invoke(contract)  # quote, chain, earnings and ex-dividend dates
    tools.compare_strategies.invoke(contract)
    market = alt.Market(recorder, ticker, config.RISK_FREE_RATE)
    for expiration in alt.expiration_choices(contract["expiration"], market):  # every chain the ToT search can visit
        recorder.get_option_chain(ticker, expiration)
    for period in HISTORY_PERIODS:
        recorder.get_price_history(ticker, period)
    recorder.get_next_earnings_date(ticker)
    recorder.record_headlines(ticker)
    return contract


def main(limit: int | None, specs: str = "core") -> None:
    recorder = RecordingProvider(YFinanceProvider())
    tools.provider = recorder
    contracts = []
    for spec in SPEC_SETS[specs][:limit]:
        contract = record_contract(recorder, spec)
        contracts.append(contract)
        print(f"{contract['ticker']} {contract['strike']:g} {contract['option_type']} {contract['expiration']} "
              f"- {len(recorder.headlines[contract['ticker']])} headlines", flush=True)
    suffix = "" if specs == "core" else f"-{specs}"
    path = recorder.save(OUT_DIR / f"{clock.today().isoformat()}{suffix}.json.gz", contracts)
    replay = SnapshotProvider(path)
    print(f"Saved {path.relative_to(config.PROJECT_ROOT)} ({path.stat().st_size / 1e6:.1f} MB, "
          f"{len(replay.calls)} calls, recorded {replay.recorded_at:%Y-%m-%d %H:%M} UTC)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None, help="only the first N contracts")
    parser.add_argument("--specs", default="core", choices=list(SPEC_SETS), help="contract set: core or scenarios")
    args = parser.parse_args()
    main(args.limit, args.specs)
