"""Semantic search over a ticker's recent headlines, with MMR to drop near-duplicate coverage."""

from options_trade_analyzer import config
from options_trade_analyzer.data.news import Headline, fetch_headlines
from options_trade_analyzer.retrieval.vector_index import Hit, VectorIndex

# News is broad and redundant, so lambda favors diversity; stale stories are excluded outright.
TOP_K = 5
FETCH_K = 25
LAMBDA = 0.4
MAX_AGE_DAYS = 14


def search_news(ticker: str, query: str, headlines: list[Headline] | None = None) -> list[Hit]:
    if headlines is None:
        headlines = fetch_headlines(ticker)
    fresh = [h for h in headlines if h.age_days <= MAX_AGE_DAYS]
    if not fresh:
        return []
    index = VectorIndex(config.get_embeddings(), "search_document: ", "search_query: ")
    index.add(
        [h.title for h in fresh],
        [{"source": h.source, "date": h.published.date().isoformat(), "link": h.link} for h in fresh],
    )
    return index.search(query, k=TOP_K, fetch_k=FETCH_K, lambda_mult=LAMBDA)
