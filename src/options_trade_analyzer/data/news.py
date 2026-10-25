"""Recent headlines for a ticker from public RSS feeds (Yahoo Finance and Google News, no API key).

Coverage is highly redundant (one story, many outlets), which is why retrieval over news uses MMR.
"""

import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
]


@dataclass
class Headline:
    title: str
    source: str
    published: datetime
    link: str

    @property
    def age_days(self) -> float:
        return (datetime.now(timezone.utc) - self.published).total_seconds() / 86400


def _parse(xml_bytes: bytes, default_source: str) -> list[Headline]:
    headlines = []
    for item in ET.fromstring(xml_bytes).findall(".//item"):
        title = (item.findtext("title") or "").strip()
        source = item.findtext("source") or default_source
        # Google News appends " - Outlet" to titles; keep the outlet as the source instead.
        if " - " in title and default_source == "Google News":
            title, source = title.rsplit(" - ", 1)
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        if title:
            headlines.append(Headline(title, source.strip(), published, item.findtext("link") or ""))
    return headlines


def fetch_headlines(ticker: str, timeout: float = 15) -> list[Headline]:
    """All headlines from every feed that responds; a failing feed is skipped, not fatal."""
    headlines = []
    for url, name in zip(FEEDS, ["Yahoo Finance", "Google News"]):
        request = urllib.request.Request(url.format(ticker=quote_plus(ticker)), headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                headlines += _parse(response.read(), name)
        except (OSError, ET.ParseError):
            continue
    return headlines
