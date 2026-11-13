"""Build the missing-data snapshot (Week 5 feedback): the scenario snapshot with one piece of data removed
per contract, so the evaluation sees how the system behaves when a free data source fails.

Synthetic by design: the recorded data is real, the gaps are made here, one per contract, and each mimics a
failure the free sources have (a blank implied volatility, a failed history call, no headlines, chains that
did not load, no market maker quoting the option, no earnings date). A removed call makes the replay raise,
the same way a failed live call does.

Run with:  uv run python scripts/make_missing_data_snapshot.py   -> data/snapshots/2026-11-13-missing.json.gz
"""

import gzip
import json

from options_trade_analyzer import config

SOURCE = config.PROJECT_ROOT / "data" / "snapshots" / "2026-11-13-scenarios.json.gz"
OUT = config.PROJECT_ROOT / "data" / "snapshots" / "2026-11-13-missing.json.gz"
GAPS = {  # ticker -> what is removed (the contract is the scenario snapshot's contract for that ticker)
    "WMT": "implied volatility blank for the contract's strike",
    "HD": "price history unavailable",
    "MSFT": "no headlines",
    "AMD": "option chains for later expirations did not load",
    "SPY": "no bid or ask for the contract (no market maker quoting it)",
    "KO": "no earnings date (as recorded: the data source had none)",
}


def contract_row(data: dict, contract: dict) -> dict:
    chain = data["calls"][f"get_option_chain|{contract['ticker']}|{contract['expiration']}"]
    return next(r for r in chain[f"{contract['option_type']}s"] if r["strike"] == contract["strike"])


def main() -> None:
    data = json.loads(gzip.decompress(SOURCE.read_bytes()))
    contracts = {c["ticker"]: c for c in data["contracts"]}
    calls = data["calls"]

    contract_row(data, contracts["WMT"])["impliedVolatility"] = None
    for period in ("6mo", "2y"):
        calls.pop(f"get_price_history|HD|{period}", None)
    data["headlines"]["MSFT"] = []
    amd = contracts["AMD"]
    for key in [k for k in calls if k.startswith("get_option_chain|AMD|") and not k.endswith(amd["expiration"])]:
        calls.pop(key)
    row = contract_row(data, contracts["SPY"])
    row["bid"], row["ask"] = 0.0, 0.0
    assert calls.get("get_next_earnings_date|KO") is None, "KO was chosen because its earnings date is missing"

    data["contracts"] = [contracts[t] for t in GAPS]
    data["gaps"] = GAPS
    OUT.write_bytes(gzip.compress(json.dumps(data).encode()))
    print(f"Saved {OUT.relative_to(config.PROJECT_ROOT)}: {len(GAPS)} contracts, one gap each")


if __name__ == "__main__":
    main()
