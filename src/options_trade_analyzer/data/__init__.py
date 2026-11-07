import functools

from options_trade_analyzer.data.provider import MarketDataProvider, YFinanceProvider


def get_provider(name: str = "yfinance") -> MarketDataProvider:
    if name == "yfinance":
        return YFinanceProvider()
    raise ValueError(f"Unknown data provider: {name!r}")


class CachingProvider:
    """Memoizes every provider call, so every agent and setup in one run sees identical market data."""

    def __init__(self, inner):
        self._inner = inner
        self._cached = {}

    def __getattr__(self, name):
        if name not in self._cached:
            self._cached[name] = functools.lru_cache(maxsize=None)(getattr(self._inner, name))
        return self._cached[name]


__all__ = ["CachingProvider", "MarketDataProvider", "YFinanceProvider", "get_provider"]
