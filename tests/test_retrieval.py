"""Offline tests for chunking, cosine search, the similarity floor, MMR and index caching.

A tiny bag-of-words embedding stands in for the real model, so no network or Ollama is needed.
"""

import numpy as np
from langchain_core.embeddings import Embeddings

from options_trade_analyzer.retrieval.knowledge import chunk_note, load_chunks
from options_trade_analyzer.retrieval.vector_index import VectorIndex, mmr_select, normalize

VOCAB = ["volatility", "earnings", "decay", "theta", "spread", "liquidity", "apple", "weather"]


class WordCountEmbeddings(Embeddings):
    def _embed(self, text: str) -> list[float]:
        words = text.lower().split()
        return [float(words.count(v)) for v in VOCAB]

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)


def make_index() -> VectorIndex:
    index = VectorIndex(WordCountEmbeddings())
    index.add(
        ["earnings volatility crush", "earnings volatility crush again", "theta decay", "spread liquidity"],
        [{"source": "a"}, {"source": "a-copy"}, {"source": "b"}, {"source": "c"}],
    )
    return index


def test_chunk_note_one_chunk_per_section_with_title():
    chunks = chunk_note("iv", "# Implied volatility\n\n## What\nIV is a forecast.\n\n## Why\nIt prices risk.")
    assert [c["metadata"]["source"] for c in chunks] == ["iv#1", "iv#2"]
    assert chunks[0]["text"] == "Implied volatility | What: IV is a forecast."


def test_chunk_note_splits_long_sections():
    chunks = chunk_note("long", "# T\n## S\n" + "word " * 250, max_words=100)
    assert len(chunks) == 3


def test_knowledge_base_notes_all_chunk():
    chunks = load_chunks()
    assert len(chunks) >= 30
    assert all(len(c["text"].split()) <= 130 for c in chunks)


def test_search_ranks_by_relevance():
    hits = make_index().search("theta decay", k=1, lambda_mult=1.0)
    assert hits[0].metadata["source"] == "b"
    assert hits[0].score > 0.99


def test_min_score_filters_off_topic_queries():
    assert make_index().search("weather", k=3, min_score=0.5) == []


def test_mmr_skips_near_duplicates():
    index = make_index()
    relevance_only = [h.metadata["source"] for h in index.search("earnings volatility decay", k=2, lambda_mult=1.0)]
    with_mmr = [h.metadata["source"] for h in index.search("earnings volatility decay", k=2, lambda_mult=0.3)]
    assert sorted(relevance_only) == ["a", "a-copy"]  # identical vectors tie
    assert with_mmr[1] == "b"


def test_mmr_select_with_lambda_one_is_pure_relevance():
    query = normalize(np.array([1.0, 0.0]))
    candidates = normalize(np.array([[0.2, 1.0], [1.0, 0.1], [1.0, 0.0]]))
    assert mmr_select(query, candidates, k=3, lambda_mult=1.0) == [2, 1, 0]


def test_save_and_load_respects_fingerprint(tmp_path):
    index = make_index()
    index.save(tmp_path, "v1")
    reloaded = VectorIndex(WordCountEmbeddings())
    assert reloaded.load(tmp_path, "v1")
    assert reloaded.texts == index.texts
    assert not VectorIndex(WordCountEmbeddings()).load(tmp_path, "v2")
