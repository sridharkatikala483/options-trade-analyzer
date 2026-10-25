"""Options knowledge base: synthetic educational notes in data/knowledge/, chunked and embedded.

Chunking follows the DPR idea: one chunk per "## " section, capped at ~120 words, with the note
title and section heading prepended so a chunk stays meaningful on its own.
"""

import hashlib
from pathlib import Path

from options_trade_analyzer import config
from options_trade_analyzer.retrieval.vector_index import Hit, VectorIndex

KNOWLEDGE_DIR = config.PROJECT_ROOT / "data" / "knowledge"
INDEX_DIR = config.PROJECT_ROOT / "data" / "index" / "knowledge"
MAX_CHUNK_WORDS = 120

# Specific concept questions favor relevance (high lambda); a similarity floor filters off-topic hits.
TOP_K = 3
FETCH_K = 10
LAMBDA = 0.7
MIN_SCORE = 0.58


def chunk_note(note_id: str, markdown: str, max_words: int = MAX_CHUNK_WORDS) -> list[dict]:
    """Split one note into section chunks. Returns dicts with 'text' and 'metadata'."""
    title = note_id
    sections: list[tuple[str, list[str]]] = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.strip() and sections:
            sections[-1][1].append(line.strip())

    chunks = []
    for heading, lines in sections:
        words = " ".join(lines).split()
        for start in range(0, len(words), max_words):
            body = " ".join(words[start : start + max_words])
            chunks.append({
                "text": f"{title} | {heading}: {body}",
                "metadata": {"source": f"{note_id}#{len(chunks) + 1}", "title": title, "section": heading},
            })
    return chunks


def load_chunks(directory: Path = KNOWLEDGE_DIR) -> list[dict]:
    chunks = []
    for path in sorted(directory.glob("*.md")):
        chunks += chunk_note(path.stem, path.read_text())
    return chunks


_index: VectorIndex | None = None


def get_index() -> VectorIndex:
    """Build the index once, cached on disk and rebuilt automatically when any note changes."""
    global _index
    if _index is None:
        chunks = load_chunks()
        fingerprint = hashlib.sha256(
            (config.EMBEDDING_MODEL + "".join(c["text"] for c in chunks)).encode()
        ).hexdigest()
        _index = VectorIndex(config.get_embeddings(), "search_document: ", "search_query: ")
        if not _index.load(INDEX_DIR, fingerprint):
            _index.add([c["text"] for c in chunks], [c["metadata"] for c in chunks])
            _index.save(INDEX_DIR, fingerprint)
    return _index


def search_knowledge(query: str) -> list[Hit]:
    return get_index().search(query, k=TOP_K, fetch_k=FETCH_K, lambda_mult=LAMBDA, min_score=MIN_SCORE)
