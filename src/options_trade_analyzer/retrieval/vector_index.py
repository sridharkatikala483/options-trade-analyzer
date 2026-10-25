"""A small in-process vector index: dense embeddings, cosine search and MMR selection.

This is the same job a vector database (Chroma, FAISS) does, kept in numpy so every step of
retrieval is visible and testable offline. Embeddings come from any LangChain `Embeddings`.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from langchain_core.embeddings import Embeddings


@dataclass
class Hit:
    text: str
    metadata: dict
    score: float  # cosine similarity to the query, -1..1


def normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def mmr_select(query: np.ndarray, candidates: np.ndarray, k: int, lambda_mult: float) -> list[int]:
    """Maximal Marginal Relevance over unit vectors.

    score(d) = lambda * sim(d, query) - (1 - lambda) * max sim(d, already selected).
    lambda 1.0 = pure relevance, 0.0 = pure diversity. Returns indices in selection order.
    """
    relevance = candidates @ query
    selected: list[int] = []
    remaining = list(range(len(candidates)))
    while remaining and len(selected) < k:
        if selected:
            redundancy = (candidates[remaining] @ candidates[selected].T).max(axis=1)
        else:
            redundancy = np.zeros(len(remaining))
        scores = lambda_mult * relevance[remaining] - (1 - lambda_mult) * redundancy
        best = remaining[int(np.argmax(scores))]
        selected.append(best)
        remaining.remove(best)
    return selected


@dataclass
class VectorIndex:
    embeddings: Embeddings
    doc_prefix: str = ""    # nomic-embed-text expects "search_document: " / "search_query: "
    query_prefix: str = ""
    texts: list[str] = field(default_factory=list)
    metadatas: list[dict] = field(default_factory=list)
    vectors: np.ndarray | None = None

    def add(self, texts: list[str], metadatas: list[dict]) -> None:
        new = normalize(np.array(self.embeddings.embed_documents([self.doc_prefix + t for t in texts])))
        self.vectors = new if self.vectors is None else np.vstack([self.vectors, new])
        self.texts += texts
        self.metadatas += metadatas

    def search(
        self,
        query: str,
        k: int = 3,
        fetch_k: int = 10,
        lambda_mult: float = 0.7,
        min_score: float = 0.0,
    ) -> list[Hit]:
        """Top `fetch_k` by cosine similarity, drop those below `min_score`, then pick `k` with MMR."""
        if self.vectors is None or not self.texts:
            return []
        q = normalize(np.array(self.embeddings.embed_query(self.query_prefix + query)))
        scores = self.vectors @ q
        top = [i for i in np.argsort(scores)[::-1][:fetch_k] if scores[i] >= min_score]
        if not top:
            return []
        picked = mmr_select(q, self.vectors[top], k, lambda_mult)
        return [Hit(self.texts[top[i]], self.metadatas[top[i]], float(scores[top[i]])) for i in picked]

    def save(self, directory: Path, fingerprint: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "vectors.npy", self.vectors)
        (directory / "docs.json").write_text(
            json.dumps({"fingerprint": fingerprint, "texts": self.texts, "metadatas": self.metadatas})
        )

    def load(self, directory: Path, fingerprint: str) -> bool:
        """Load a saved index; returns False if missing or built from different source documents."""
        docs_file = directory / "docs.json"
        if not docs_file.exists():
            return False
        docs = json.loads(docs_file.read_text())
        if docs["fingerprint"] != fingerprint:
            return False
        self.texts, self.metadatas = docs["texts"], docs["metadatas"]
        self.vectors = np.load(directory / "vectors.npy")
        return True
