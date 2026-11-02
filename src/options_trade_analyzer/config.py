"""Settings loaded from .env, plus the one place that decides which LLM to use."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "yfinance").lower()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.04"))
TOT_PROPOSER = os.getenv("TOT_PROPOSER", "llm").lower()  # "rules" skips the LLM in the alternative search


def get_embeddings() -> Embeddings:
    """Embedding model for retrieval. Always local Ollama, so RAG works offline and for free."""
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=EMBEDDING_MODEL)


def get_llm(provider: str | None = None, reasoning: bool = True) -> BaseChatModel:
    """Return the chat model for the configured provider.

    Switching between local Ollama and the Claude API is a one-line change in .env.
    reasoning=False turns qwen3 thinking off, for short structured replies such as the ToT menu picks
    (minutes faster per call); the Claude model is unaffected.
    """
    provider = (provider or LLM_PROVIDER).lower()
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        # temperature 0 for repeatable runs; qwen3 thinking stays on (kept out of the reply) for reliable
        # tool calls; Ollama's default 4096-token context truncates agent traces, so raise it.
        # The timeout stops a dropped connection (e.g. after the Mac sleeps) from hanging a run forever.
        return ChatOllama(model=OLLAMA_MODEL, temperature=0, reasoning=reasoning, num_ctx=16384,
                          client_kwargs={"timeout": 600})
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
        return ChatAnthropic(model=ANTHROPIC_MODEL, max_tokens=16000)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'ollama' or 'anthropic')")
