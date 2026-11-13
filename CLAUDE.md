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
uv run python scripts/record_snapshot.py   # record market data for the evaluation contracts (live, ~1 min)
DATA_PROVIDER=snapshot SNAPSHOT_PATH=data/snapshots/2026-11-06.json.gz uv run python scripts/evaluate.py ...  # replay
uv run streamlit run app.py             # dashboard at http://localhost:8501
uv add <pkg>  /  uv add --dev <pkg>     # add a dependency (updates pyproject.toml and uv.lock)
```

`.claude/launch.json` defines a headless `dashboard` launch config on port 8501.

## Layout and architecture

```
app.py                                  Streamlit dashboard: contract view, payoff chart (+ alternative), "Run AI
                                        analysis" with live agent progress, report, findings, Critic checks
src/options_trade_analyzer/
  config.py                             reads .env at import; get_llm() is the only LLM factory
  clock.py                              today()/now(): the only clock; a snapshot replay freezes it
  injection.py                          prompt-injection monitor for headlines: flagged ones are withheld, run held
  acceptance.py                         acceptance gate: thresholds and pass/fail per setup (score_reports.py prints it)
  review.py                             Checkpoint 6 outcomes (shown / warning / held for review / refused), run log
                                        data/runs/*.jsonl (gitignored), review queue and reviewer decisions
  jobs.py                               background analysis runs for the dashboard (survive reloads, one at a time)
  answer_keys.py                        what a correct report must and must not say, built from the snapshot
  data/provider.py                      MarketDataProvider Protocol + YFinanceProvider
  data/__init__.py                      get_provider(name) factory
  data/snapshot.py                      RecordingProvider (record live calls) + SnapshotProvider (replay, freezes clock)
  data/news.py                          recent headlines from public RSS (Yahoo Finance, Google News)
  analytics/options_math.py             Black-Scholes price, Greeks, breakeven, payoff (via vollib)
  analytics/data_quality.py             quote freshness, liquidity rating, model-vs-market gap, assumption flags
  analytics/strategies.py               multi-leg payoff math (Leg, max loss/gain, breakevens) for comparisons
  analytics/alternatives.py             ToT candidates: build, score out of 100, prune, rank (deterministic)
  analytics/trend.py                    price trend from daily closes (1m/3m change, 50-day average, range)
  analytics/input_risk.py               risk flags on the contract itself (short expiry, poor liquidity, closed
                                        market, low chance beyond breakeven), shown above the report
  analytics/risk_metrics.py             risk-adjusted measures: expected P/L (Black-Scholes and past moves),
                                        bid-ask cost, IV shifts, max gain per $ risked
  retrieval/vector_index.py             numpy vector index: cosine search, similarity floor, MMR
  retrieval/knowledge.py                knowledge-base chunking + cached index (data/index/, gitignored)
  retrieval/news.py                     per-request headline index with MMR and 14-day cutoff
  agents/tools.py                       LangChain tools (contract + data_quality, Greeks, earnings date,
                                        compare_strategies, search_alternatives, price trend, 2 retrieval tools)
  agents/tot_search.py                  Tree-of-Thought beam search (LangGraph loop, LLM or rule proposer)
  agents/options_agent.py               Options Analysis ReAct agent; analyze_contract(..., use_retrieval,
                                        verify_report, use_tot) with up to 2 verification-driven revisions
  agents/team.py                        Checkpoint 5 multi-agent graph: coordinator (code), Options Analyst +
                                        Market Context in parallel, Risk Strategist, Writer, rule-based Critic
                                        routing fixes to the owning agent; analyze_contract_team(...)
  agents/critic.py                      LLM Critic: judgment checklist after the rules pass; JSON reply names the owner
  agents/verifier.py                    rule-based report checks: tool completeness, numbers, dates,
                                        liquidity wording, citations, no advice, required statements,
                                        overconfident wording
scripts/record_snapshot.py              record the evaluation contracts' market data -> data/snapshots/<date>.json.gz
scripts/check_setup.py                  environment smoke test (exits 1 on failure)
tests/test_options_math.py              textbook-value tests for the math
tests/test_reliability.py               independent Black-Scholes cross-check, data-quality and strategy tests
tests/test_retrieval.py                 offline chunking, search, similarity floor and MMR tests
tests/test_verifier.py                  verifier catches the real flawed run and passes a faithful report
tests/test_tot.py                       ToT search on a synthetic Black-Scholes chain (scoring, pruning, beam)
tests/test_critic.py                    LLM Critic reply parsing (owners, failures, cap) with a stand-in LLM
tests/test_snapshot.py                  record/replay round trip; a later replay gives identical tool output
tests/test_jobs.py                      background jobs: progress wording, one at a time, errors kept
tests/test_team.py                      team wiring with stand-in LLM calls: join, routing, failures, stop
tests/test_risk_metrics.py              risk-adjusted measures on the same synthetic chain
tests/test_injection.py                 injection patterns, ordinary headlines pass, news tool withholds and holds the run
tests/test_acceptance.py                acceptance thresholds, measures from saved runs, hand-confirmed false alarms
tests/test_review.py                    outcome rules, run log round trip, review queue and decisions
tests/test_input_risk.py                input risk flags and the chance-beyond-breakeven estimate
tests/test_answer_keys.py               answer-key items and scoring on short reports with planted mistakes
scripts/retrieval_demo.py               with/without-retrieval comparison -> docs/retrieval_demo.md
scripts/evaluate.py                     10 contracts x 3 setups, resumable -> docs/evaluation/ (hours on local qwen3)
scripts/score_reports.py                score reports against answer keys + acceptance gate -> docs/evaluation/quality_<name>.md
scripts/injection_eval.py               injection monitor on planted (direct, paraphrased, held-out) and 914 real headlines
scripts/evaluate_tot.py                 ToT vs fixed spread vs exhaustive, plus risk-adjusted measures -> docs/evaluation/tot_summary*.md
data/knowledge/                         synthetic options-education notes (the RAG corpus)
data/snapshots/                         recorded market data (gzipped JSON) for repeatable evaluation runs; the
                                        -scenarios snapshot covers more conditions (evaluate.py --specs scenarios)
data/answer_keys/hand_checks.json       flags a person ruled out as false alarms, each with a note (used by the gate)
```

Key seams to keep intact:

- **LLM switch:** always obtain models with `config.get_llm()`. `LLM_PROVIDER` in `.env` selects
  `ollama` (local `qwen3:8b`, free, for development) or `anthropic` (`ANTHROPIC_MODEL`, needs
  `ANTHROPIC_API_KEY`). Don't instantiate `ChatOllama`/`ChatAnthropic` elsewhere.
- **Data access:** go through `get_provider(config.DATA_PROVIDER)` and the `MarketDataProvider`
  interface, never call `yfinance` directly outside `provider.py`. A new source (Schwab, a snapshot
  replay provider) is a new class implementing the same six methods, registered in `get_provider`.
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
  Exception: the ToT proposer uses `get_llm(reasoning=False)` for its short menu picks (~7 s per call instead
  of ~6 min); an empty reply there just falls back to the default choices. `get_llm` caps each qwen3 reply at
  8,192 tokens (`num_predict`): qwen3 sometimes loops in its thinking, and a still-streaming reply never hits the timeout.
- Read model replies with `message.text`, not `.content`: Claude returns thinking blocks in a content list.
- yfinance `.news` currently returns nothing; headlines come from RSS in `data/news.py` instead.
- `TOT_PROPOSER=rules` runs the alternative search without LLM calls (default `llm`); off-menu or
  unparseable proposals fall back to the default choices and are counted in the tool output.
- `FINNHUB_API_KEY` and the Schwab keys are defined in `.env.example` but not used by code yet.
- Tests should be deterministic and offline (no network, no LLM). Use `data/snapshots/` for market data.
- Never call `date.today()` or `datetime.now()` directly: use `clock.today()` / `clock.now()`, or a snapshot
  replay will see the wrong day (days to expiry, quote age and news age all drift). Log timestamps (when a
  person ran or reviewed something) use `clock.wall_now()`, which is never frozen.
- Never commit `.env`, `data/history.db` (planned SQLite long-term memory), `data/runs/` (the run and review
  log), or `.streamlit/secrets.toml`.
- Style: short module docstrings, type hints, small functions, `Literal["call", "put"]` for option type.

## Planned next steps (from DESIGN.md)

Repeat the comparison with the required-statement fix on Claude Haiku → SQLite memory →
LLM vs rule proposer on more contracts.
