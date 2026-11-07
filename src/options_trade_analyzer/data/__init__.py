import functools

from options_trade_analyzer.data.provider import MarketDataProvider, YFinanceProvider


def get_provider(name: str = "yfinance") -> MarketDataProvider:
    if name == "yfinance":
        return YFinanceProvider()
    if name == "snapshot":  # replay recorded data; freezes the clock at the recording time
        from options_trade_analyzer import config
        from options_trade_analyzer.data.snapshot import SnapshotProvider

        if not config.SNAPSHOT_PATH:
            raise ValueError("DATA_PROVIDER=snapshot needs SNAPSHOT_PATH (a file in data/snapshots/)")
        return SnapshotProvider(config.PROJECT_ROOT / config.SNAPSHOT_PATH).activate()
    raise ValueError(f"Unknown data provider: {name!r} (use 'yfinance' or 'snapshot')")


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
