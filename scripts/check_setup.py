"""Checks that market data and the configured LLM both work.

Run with:  uv run python scripts/check_setup.py
"""

import sys

from options_trade_analyzer import config
from options_trade_analyzer.data import get_provider


def check_market_data() -> bool:
    try:
        provider = get_provider(config.DATA_PROVIDER)
        price = provider.get_quote("AAPL")
        expirations = provider.get_expirations("AAPL")
        chain = provider.get_option_chain("AAPL", expirations[0])
        print(f"[ok]   Market data: AAPL ${price:.2f}, {len(expirations)} expirations, "
              f"{len(chain['calls'])} calls on {expirations[0]}")
        return True
    except Exception as exc:
        print(f"[fail] Market data: {exc}")
        return False


def check_llm() -> bool:
    try:
        llm = config.get_llm()
        reply = llm.invoke("Reply with exactly: ready")
        print(f"[ok]   LLM ({config.LLM_PROVIDER}): {str(reply.content).strip()[:60]}")
        return True
    except Exception as exc:
        print(f"[fail] LLM ({config.LLM_PROVIDER}): {exc}")
        return False


if __name__ == "__main__":
    results = [check_market_data(), check_llm()]
    sys.exit(0 if all(results) else 1)
