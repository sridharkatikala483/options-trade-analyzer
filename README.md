# AI Options Trade Analyzer

A multi-agent AI system (Forecaster option) that evaluates a proposed options trade and produces an explainable risk assessment. For education only; it never places trades.

The full design (agents, reasoning loop, memory, tools, evaluation plan and build checklist) is in [docs/DESIGN.md](docs/DESIGN.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and, for the free local LLM, [Ollama](https://ollama.com).

```bash
uv sync                      # installs Python 3.12 and all dependencies into .venv
cp .env.example .env         # then edit .env
ollama pull qwen3:8b         # local model (about 5 GB), only needed for LLM_PROVIDER=ollama
ollama pull nomic-embed-text # embedding model for retrieval (about 270 MB), always needed
```

## Switching LLMs

Set `LLM_PROVIDER` in `.env`:

- `ollama` - free, runs locally (`OLLAMA_MODEL=qwen3:8b`)
- `anthropic` - Claude API; also set `ANTHROPIC_API_KEY`. Use `claude-haiku-5-5` for low-cost bulk testing.

## Common commands

```bash
uv run python scripts/check_setup.py   # verify market data and the LLM both work
uv run pytest                          # unit tests for the options math
uv run streamlit run app.py            # open the dashboard at http://localhost:8501
uv run python scripts/retrieval_demo.py  # agent with vs without retrieval -> docs/retrieval_demo.md
```

## Project layout

```
app.py                              Streamlit dashboard
src/options_trade_analyzer/
  config.py                         settings and get_llm() model switch
  data/provider.py                  MarketDataProvider interface + yfinance implementation
  analytics/options_math.py         Black-Scholes price, Greeks, breakeven, payoff
  agents/                           LangGraph agents (to be built)
scripts/check_setup.py              environment check
tests/                              pytest tests
data/snapshots/                     saved market data for offline testing and demos
```
