"""Settings loaded from .env, plus the one place that decides which LLM to use."""

import os

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "yfinance").lower()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def get_llm(provider: str | None = None) -> BaseChatModel:
    """Return the chat model for the configured provider.

    Switching between local Ollama and the Claude API is a one-line change in .env.
    """
    provider = (provider or LLM_PROVIDER).lower()
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=OLLAMA_MODEL)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
        return ChatAnthropic(model=ANTHROPIC_MODEL, max_tokens=16000)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'ollama' or 'anthropic')")
