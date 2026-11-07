"""Market data access behind one interface, so yfinance can later be swapped for Schwab."""

import datetime as dt
import time
from typing import Protocol

import pandas as pd
import yfinance as yf


class MarketDataProvider(Protocol):
    def get_quote(self, ticker: str) -> float: ...

    def get_price_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame: ...

    def get_expirations(self, ticker: str) -> list[str]: ...

    def get_option_chain(self, ticker: str, expiration: str) -> dict[str, pd.DataFrame]: ...

    def get_next_earnings_date(self, ticker: str) -> dt.date | None: ...

    def get_next_ex_dividend_date(self, ticker: str) -> dt.date | None: ...


class YFinanceProvider:
    """Free data from Yahoo Finance. Unofficial and sometimes delayed."""

    def get_quote(self, ticker: str) -> float:
        history = yf.Ticker(ticker).history(period="5d")
        if history.empty:
            raise ValueError(f"No price data for {ticker}")
        return float(history["Close"].iloc[-1])

    def get_price_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        # Yahoo sometimes returns an empty frame for a listed ticker ("possibly delisted"); try once more
        history = yf.Ticker(ticker).history(period=period)
        if history.empty:
            time.sleep(2)
            history = yf.Ticker(ticker).history(period=period)
        return history

    def get_expirations(self, ticker: str) -> list[str]:
        return list(yf.Ticker(ticker).options)

    def get_option_chain(self, ticker: str, expiration: str) -> dict[str, pd.DataFrame]:
        chain = yf.Ticker(ticker).option_chain(expiration)
        return {"calls": chain.calls, "puts": chain.puts}

    def get_next_earnings_date(self, ticker: str) -> dt.date | None:
        """Next scheduled earnings date on or after today, or None if Yahoo has none."""
        dates = self._calendar(ticker).get("Earnings Date") or []
        upcoming = [d for d in dates if d >= dt.date.today()]
        return min(upcoming) if upcoming else None

    def get_next_ex_dividend_date(self, ticker: str) -> dt.date | None:
        """Next ex-dividend date on or after today, or None if none is announced."""
        date = self._calendar(ticker).get("Ex-Dividend Date")
        return date if isinstance(date, dt.date) and date >= dt.date.today() else None

    @staticmethod
    def _calendar(ticker: str) -> dict:
        """Yahoo's events calendar; ETFs and some tickers have none (Yahoo answers 404)."""
        try:
            return yf.Ticker(ticker).calendar or {}
        except Exception:
            return {}
