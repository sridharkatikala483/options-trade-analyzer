# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A capstone project: a multi-agent AI system (LangGraph) that evaluates a proposed options trade
(ticker, call/put, strike, expiration) and writes a plain-language risk assessment. **Education only —
nothing in this codebase may place, prepare, or simulate submitting an order.**

`docs/DESIGN.md` is the source of truth for the design: agents, reasoning loop, memory, tools,
evaluation plan, and the implementation checklist. Read it before adding agent code, and update it
(including the "Implementation status" checklist) when the design or progress changes.

## Commands

All commands go through `uv` (Python 3.12, deps in `.venv`). Run `uv sync` first if imports fail —
the package uses a `src/` layout and is installed into the venv by `uv sync`.

```bash
uv sync                                 # install/refresh dependencies
uv run pytest                           # all tests
uv run pytest tests/test_options_math.py::test_breakeven   # one test
uv run python scripts/check_setup.py    # live check: yfinance data + configured LLM
uv run streamlit run app.py             # dashboard at http://localhost:8501
uv add <pkg>  /  uv add --dev <pkg>     # add a dependency (updates pyproject.toml and uv.lock)
```

`.claude/launch.json` defines a headless `dashboard` launch config on port 8501.

## Layout and architecture

```
app.py                                  Streamlit + Plotly dashboard (single-contract view, payoff chart)
src/options_trade_analyzer/
  config.py                             reads .env at import; get_llm() is the only LLM factory
  data/provider.py                      MarketDataProvider Protocol + YFinanceProvider
  data/__init__.py                      get_provider(name) factory
  data/news.py                          recent headlines from public RSS (Yahoo Finance, Google News)
  analytics/options_math.py             Black-Scholes price, Greeks, breakeven, payoff (via vollib)
  analytics/data_quality.py             quote freshness, liquidity rating, model-vs-market gap, assumption flags
  analytics/strategies.py               multi-leg payoff math (Leg, max loss/gain, breakevens) for comparisons
  retrieval/vector_index.py             numpy vector index: cosine search, similarity floor, MMR
  retrieval/knowledge.py                knowledge-base chunking + cached index (data/index/, gitignored)
  retrieval/news.py                     per-request headline index with MMR and 14-day cutoff
  agents/tools.py                       LangChain tools (contract + data_quality, Greeks, earnings date,
                                        compare_strategies, 2 retrieval tools)
  agents/options_agent.py               Options Analysis ReAct agent; analyze_contract(..., use_retrieval,
                                        verify_report) with up to 2 verification-driven revisions
  agents/verifier.py                    rule-based report checks: tool completeness, numbers, dates,
                                        liquidity wording, citations, no advice
scripts/check_setup.py                  environment smoke test (exits 1 on failure)
tests/test_options_math.py              textbook-value tests for the math
tests/test_reliability.py               independent Black-Scholes cross-check, data-quality and strategy tests
tests/test_retrieval.py                 offline chunking, search, similarity floor and MMR tests
tests/test_verifier.py                  verifier catches the real flawed run and passes a faithful report
scripts/retrieval_demo.py               with/without-retrieval comparison -> docs/retrieval_demo.md
scripts/evaluate.py                     10 contracts x 3 setups, resumable -> docs/evaluation/ (hours on local qwen3)
data/knowledge/                         synthetic options-education notes (the RAG corpus)
data/snapshots/                         saved market data for repeatable evaluation scenarios
```

Key seams to keep intact:

- **LLM switch:** always obtain models with `config.get_llm()`. `LLM_PROVIDER` in `.env` selects
  `ollama` (local `qwen3:8b`, free, for development) or `anthropic` (`ANTHROPIC_MODEL`, needs
  `ANTHROPIC_API_KEY`). Don't instantiate `ChatOllama`/`ChatAnthropic` elsewhere.
- **Data access:** go through `get_provider(config.DATA_PROVIDER)` and the `MarketDataProvider`
  interface, never call `yfinance` directly outside `provider.py`. A new source (Schwab, a snapshot
  replay provider) is a new class implementing the same four methods, registered in `get_provider`.
- **Embeddings:** `config.get_embeddings()` (local Ollama `nomic-embed-text`; run `ollama pull
  nomic-embed-text`). Knowledge index rebuilds automatically when `data/knowledge/*.md` changes.
- **Tools** return JSON strings and report bad input as `{"error": ...}` rather than raising, so the
  agent can observe and correct (ReAct error recovery).
- **Math:** all numeric calculation lives in `analytics/`. The LLM interprets tool outputs; it never
  computes numbers itself, and every number in a final report must match a tool output.

## Conventions and gotchas

- `options_math` units: `years` is time to expiry in years; `rate` and `iv` are decimals (0.05, 0.20);
  theta is per calendar day; vega and rho are per 1 percentage point. `payoff_at_expiry` returns
  dollars for a **long** position, 100 shares per contract.
- Black-Scholes is European-style; US equity options are American, so values are approximations —
  reports must say so.
- `get_option_chain` returns `{"calls": DataFrame, "puts": DataFrame}` with yfinance column names
  (`strike`, `lastPrice`, `impliedVolatility`, `volume`, `openInterest`, `bid`, `ask`, ...).
- `config` calls `load_dotenv()` at import time; settings are module-level constants.
- yfinance is unofficial and can be delayed or empty — handle missing data explicitly (retry, fallback,
  then mark low confidence, per DESIGN.md).
- On local `qwen3:8b`, keep `reasoning=True` and `num_ctx=16384`: with thinking off it often stops early with an empty
  reply, and Ollama's default 4096-token context silently truncates the trace. One run takes minutes.
- yfinance `.news` currently returns nothing; headlines come from RSS in `data/news.py` instead.
- `FINNHUB_API_KEY` and the Schwab keys are defined in `.env.example` but not used by code yet.
- Tests should be deterministic and offline (no network, no LLM). Use `data/snapshots/` for market data.
- Never commit `.env`, `data/history.db` (planned SQLite long-term memory), or `.streamlit/secrets.toml`.
- Style: short module docstrings, type hints, small functions, `Literal["call", "put"]` for option type.

## Planned next steps (from DESIGN.md)

Remaining specialists → LangGraph orchestration with shared state and an
LLM Critic on top of the rule-based verifier → SQLite memory → report in the dashboard → evaluation harness
(scenarios with answer keys, run with and without the Critic).
