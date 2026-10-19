from options_trade_analyzer.data.provider import MarketDataProvider, YFinanceProvider


def get_provider(name: str = "yfinance") -> MarketDataProvider:
    if name == "yfinance":
        return YFinanceProvider()
    raise ValueError(f"Unknown data provider: {name!r}")


__all__ = ["MarketDataProvider", "YFinanceProvider", "get_provider"]
