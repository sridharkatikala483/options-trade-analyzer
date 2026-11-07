"""Snapshots: record every market-data and news call once, then replay it later.

A replay gives every setup and every later re-run identical inputs: the same quotes, option chains,
earnings dates, price history and headlines, and the same clock (frozen at the recording time, so days
to expiry, quote age and news age do not drift). Files are gzipped JSON in data/snapshots/.

    recorder = RecordingProvider(YFinanceProvider())   # use it like any provider, then
    recorder.save(path, contracts)
    provider = SnapshotProvider(path).activate()       # replays; DATA_PROVIDER=snapshot does this
"""

import datetime as dt
import gzip
import json
from pathlib import Path

import pandas as pd

from options_trade_analyzer import clock
from options_trade_analyzer.data import news
from options_trade_analyzer.data.news import Headline

CHAIN_COLUMNS = ("strike", "lastPrice", "bid", "ask", "impliedVolatility", "volume", "openInterest", "lastTradeDate")
NUMERIC_COLUMNS = CHAIN_COLUMNS[:-1]


def _key(method: str, *args) -> str:
    return "|".join([method, *map(str, args)])


def _chain_to_rows(df: pd.DataFrame) -> list[dict]:
    out = df[[c for c in CHAIN_COLUMNS if c in df.columns]].copy()
    if "lastTradeDate" in out:
        out["lastTradeDate"] = out["lastTradeDate"].map(lambda t: t.isoformat() if pd.notna(t) else None)
    return out.astype(object).where(out.notna(), None).to_dict("records")


def _rows_to_chain(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for column in NUMERIC_COLUMNS:
        if column in df:
            df[column] = pd.to_numeric(df[column])  # a recorded null becomes NaN again
    if "lastTradeDate" in df:
        df["lastTradeDate"] = pd.to_datetime(df["lastTradeDate"], utc=True)
    return df


def _date_out(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


class RecordingProvider:
    """Passes every call through to a live provider and keeps a copy of the answer."""

    def __init__(self, inner):
        self.inner, self.calls, self.headlines = inner, {}, {}

    def get_quote(self, ticker: str) -> float:
        value = float(self.inner.get_quote(ticker))
        self.calls[_key("get_quote", ticker)] = value
        return value

    def get_price_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        history = self.inner.get_price_history(ticker, period)
        self.calls[_key("get_price_history", ticker, period)] = {
            "dates": [d.isoformat() for d in history.index], "close": [float(x) for x in history["Close"]]}
        return history

    def get_expirations(self, ticker: str) -> list[str]:
        value = list(self.inner.get_expirations(ticker))
        self.calls[_key("get_expirations", ticker)] = value
        return value

    def get_option_chain(self, ticker: str, expiration: str) -> dict[str, pd.DataFrame]:
        chain = self.inner.get_option_chain(ticker, expiration)
        self.calls[_key("get_option_chain", ticker, expiration)] = {k: _chain_to_rows(v) for k, v in chain.items()}
        return chain

    def get_next_earnings_date(self, ticker: str) -> dt.date | None:
        value = self.inner.get_next_earnings_date(ticker)
        self.calls[_key("get_next_earnings_date", ticker)] = _date_out(value)
        return value

    def get_next_ex_dividend_date(self, ticker: str) -> dt.date | None:
        value = self.inner.get_next_ex_dividend_date(ticker)
        self.calls[_key("get_next_ex_dividend_date", ticker)] = _date_out(value)
        return value

    def record_headlines(self, ticker: str) -> list[Headline]:
        headlines = news.fetch_headlines(ticker)
        self.headlines[ticker] = [{"title": h.title, "source": h.source, "published": h.published.isoformat(),
                                   "link": h.link} for h in headlines]
        return headlines

    def save(self, path: Path, contracts: list[dict]) -> Path:
        payload = {"recorded_at": clock.now().isoformat(), "today": clock.today().isoformat(),
                   "contracts": contracts, "calls": self.calls, "headlines": self.headlines}
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(payload, f)
        return path


class SnapshotProvider:
    """Answers from a recorded snapshot; a call that was never recorded is an error, not a live fetch."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        with gzip.open(self.path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        self.calls, self.contracts = data["calls"], data["contracts"]
        self.recorded_at = dt.datetime.fromisoformat(data["recorded_at"])
        self.today = dt.date.fromisoformat(data["today"])
        self.headlines = {t: [Headline(h["title"], h["source"], dt.datetime.fromisoformat(h["published"]), h["link"])
                              for h in items] for t, items in data["headlines"].items()}

    def activate(self) -> "SnapshotProvider":
        """Freeze the clock at the recording time and serve the recorded headlines."""
        clock.freeze(self.recorded_at, self.today)
        news.REPLAY = self.headlines
        return self

    def _get(self, method: str, *args):
        key = _key(method, *args)
        if key not in self.calls:
            raise KeyError(f"not in snapshot {self.path.name}: {method}({', '.join(map(str, args))})")
        return self.calls[key]

    def get_quote(self, ticker: str) -> float:
        return self._get("get_quote", ticker)

    def get_price_history(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        data = self._get("get_price_history", ticker, period)
        return pd.DataFrame({"Close": data["close"]}, index=pd.to_datetime(data["dates"], utc=True))

    def get_expirations(self, ticker: str) -> list[str]:
        return list(self._get("get_expirations", ticker))

    def get_option_chain(self, ticker: str, expiration: str) -> dict[str, pd.DataFrame]:
        return {k: _rows_to_chain(v) for k, v in self._get("get_option_chain", ticker, expiration).items()}

    def get_next_earnings_date(self, ticker: str) -> dt.date | None:
        value = self._get("get_next_earnings_date", ticker)
        return dt.date.fromisoformat(value) if value else None

    def get_next_ex_dividend_date(self, ticker: str) -> dt.date | None:
        value = self._get("get_next_ex_dividend_date", ticker)
        return dt.date.fromisoformat(value) if value else None
