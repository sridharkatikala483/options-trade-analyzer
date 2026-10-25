# Design Spec: AI-Powered Options Trade Analyzer

The implementation reference for this project, distilled from the submitted capstone checkpoints
(Checkpoint 1: scoping and initial agent design; Checkpoint 2: reasoning, memory and tool use) and the
instructor's feedback. Update this file when the design changes.

## Agent concept

- **Course option:** Forecaster agent.
- **Task:** given a proposed options trade (ticker, call or put, strike, expiration), produce a
  plain-language assessment: breakeven, maximum loss, P&L scenarios, key risks, bullish and bearish
  considerations, and a lower-risk alternative strategy.
- **User:** self-directed retail investor or finance student who knows stocks but is new to options.
- **Core problem it catches:** traders who are right about direction but still lose money (for example,
  implied volatility collapsing after earnings, or extreme time decay near expiry).

## Non-negotiable rules

1. Education only. No tool can place or prepare an order.
2. All math is deterministic Python (`analytics/`). The LLM never calculates; it interprets.
3. Every number in the final report must match a tool output (consistency check).
4. Market data is always fetched fresh; long-term memory figures are only for comparison.
5. Missing or stale data: retry, then fall back to a backup source, then mark the finding low confidence.
6. The Critic revision loop runs at most 2 rounds, so every analysis terminates.
7. Every report states known limits (Black-Scholes approximates American-style options; news may be misread).

## Agents

| Agent | Responsibility | Tools |
| --- | --- | --- |
| Orchestrator | Validates input, loads market data, assigns work, merges results | none |
| Stock Analysis | Price trend, recent performance, key price levels | price history lookup, technical indicators |
| Options Analysis | Premium, liquidity (volume, open interest, bid-ask spread), implied volatility, Greeks | option chain lookup, Greeks calculator |
| News and Sentiment | Earnings dates, catalysts, headline tone | news search (Finnhub), earnings calendar |
| Risk Analysis | Max loss, breakeven, time decay, volatility exposure, alternatives | payoff calculator, strategy comparison |
| Critic | Tests assumptions, flags weak or conflicting findings | reads all agents' findings |

The four specialists run in parallel after the Orchestrator, then the Critic reviews, then the report.

Strategies to compare: long call/put, vertical spread, covered call, cash-secured put.

## Reasoning loop

- **Inner loop (each specialist): ReAct.** Reason (what is still unknown?) -> Act (call a tool) ->
  Observe (read the result, update the plan) -> repeat until no open questions, then write a finding
  with its evidence.
  - Observations change the path. Examples: low volume -> check bid-ask spread; expiry tomorrow -> focus
    on time decay; expiry just after earnings -> reprice at lower IV to test a volatility drop.
- **Outer loop: Critic.** Reviews all findings together. A conflict (e.g. bullish trend + option too
  short-dated to benefit) is sent back as a new observation to the agent that must revise. Max 2 rounds.
- **Tool-use rule:** whenever a step needs a current fact or a number, call a tool instead of answering
  from training data.

## Memory

| Type | Holds | Used | Implementation idea |
| --- | --- | --- | --- |
| Short-term (working) | Request, each agent's reasoning, tool calls and observations, Critic feedback | During one analysis; cleared after | LangGraph shared typed state |
| Long-term | Past analyses with key figures, user's risk preference, user ratings of reports | Across sessions: compare today's price/IV with last time and highlight changes; ratings refine agent instructions | SQLite (`data/history.db`) |

## Tools and the limitation each addresses

| Tool | Limitation |
| --- | --- |
| Quote, price history, option chain lookup | Retrieval: model has no current data |
| News search, earnings calendar | Retrieval + grounding: recent events and upcoming dates |
| Greeks, breakeven, payoff calculators | Computation: model makes arithmetic errors |
| Strategy comparison | Computation: many exact payoff calculations |

## Retrieval (RAG) — Checkpoint 3

Decision: retrieval **is** required, for two kinds of knowledge that tools cannot supply as numbers.

| Source | Data | Chunking | Retrieval | Why |
| --- | --- | --- | --- | --- |
| Options knowledge base | 18 synthetic notes in `data/knowledge/*.md` | One chunk per `##` section, max 120 words, `title | section` prepended (DPR style) -> 38 chunks | top 3 of 10 candidates, MMR lambda 0.7, similarity floor 0.58 | Grounds explanations (volatility crush, decay, liquidity) and makes them citable `[KB: source]` |
| Recent news | Yahoo Finance + Google News RSS headlines (public, no key) | One headline = one chunk | top 5 of 25, MMR lambda 0.4, only last 14 days | Coverage is redundant (one story, many outlets); MMR keeps distinct stories |

- Embeddings: local Ollama `nomic-embed-text` (768-d) with `search_document:` / `search_query:` prefixes.
- Vector index: `retrieval/vector_index.py` (numpy cosine + MMR), knowledge index cached in `data/index/`
  and rebuilt when notes change.
- Agent tools: `search_options_knowledge`, `search_recent_news`; `use_retrieval=False` removes them for
  comparison (`scripts/retrieval_demo.py` -> `docs/retrieval_demo.md`).
- Failure modes handled: off-topic matches (similarity floor, agent told "nothing relevant"), stale news
  (14-day cutoff), duplicate coverage (MMR), misapplied general guidance (prompt requires checking
  passages against the contract's actual numbers; observed in early runs).

## Feedback points

1. Tool results shape the next step.
2. Validation checks (missing/stale data, report-vs-tool number consistency).
3. Critic review and revision.
4. User feedback: follow-up questions and report ratings (stored in long-term memory).

## Evaluation plan (from instructor feedback on Checkpoint 1)

- 30-40 scenarios combining market conditions (rising/falling/flat trend; high/low IV; before/after
  earnings) with contract types (ITM/ATM/OTM; 1-90 days to expiry; liquid/illiquid; call/put).
  Save each scenario's market data in `data/snapshots/` so runs are repeatable.
- Each scenario has an **answer key written in advance** (risks the report must mention, planted conflicts).

| Criterion | Measure | Target |
| --- | --- | --- |
| Calculation accuracy | Report figures matching tool outputs (and Greeks vs an independent reference) | 100% |
| Risk identification | Required risks mentioned / required risks on the key | >= 90% |
| Data freshness | Stale or missing data flagged | 100% |
| Conflict detection | Planted conflicts caught | >= 90% |

- **Independent verification (Checkpoint 2 feedback):** every scenario's Greeks, prices, breakevens and
  strategy payoffs are checked against a separately written Black-Scholes and payoff calculation
  (`tests/test_reliability.py` already does this for 72 price/Greek cases and the spread example).
- **Error tracking:** count false risk omissions (answer-key risks missing from the report) and incorrect
  statements or recommendations (any recommendation to trade, misstated alternative, or number that
  does not match a tool output, such as the wrong earnings date in the Checkpoint 3 demo).
- **Critic change log:** save each report before and after Critic review, and record every change and
  whether it fixed or introduced an error.
- **Proving the Critic helps:** run every scenario with and without the Critic; plant known errors (wrong
  breakeven, missed earnings date, contradictory conclusions) and count catches; track false alarms
  (precision) and extra cost (time, LLM calls). Keep the Critic only if it raises scores without frequent
  false alarms.

## Data-quality checks (from instructor feedback on Checkpoint 2)

Computed in Python (`analytics/data_quality.py`) and returned in `get_option_contract`'s `data_quality`
block; the agent must report every item and may not judge liquidity itself.

| Check | Rule | AAPL 350 call, Nov 6, 2026 (demo) |
| --- | --- | --- |
| Quote freshness | Last trade time; `fresh` (<= 30 min) / `delayed` during the session, `market closed` otherwise | Last trade Fri 15:59 ET -> market closed |
| Liquidity | Worst of: spread <= 10% good, <= 25% fair; volume >= 100 / >= 10; open interest >= 500 / >= 100 | good (4% spread, 791 volume, 5,461 OI) |
| Model vs market | Black-Scholes price vs bid/mid/ask; flag gaps >= 5% | model $8.05 vs mid $7.50 (+7.3%), outside bid-ask -> flagged |
| Assumption flags | earnings before expiry, <= 3 days left, >= 15% out of the money, ex-dividend before expiry | earnings before expiry -> post-earnings prices are scenarios |

## Lower-risk alternative (from Checkpoint 2 feedback)

`compare_strategies` evaluates the long option and a vertical spread (sell the listed strike nearest 3%
beyond the bought strike) with the same chain mid-prices and expiration (`analytics/strategies.py`).
Demo: long 350 call costs $750 (max loss $750, breakeven $357.50, unlimited gain); 350/360 bull call
spread costs $405 (max loss $405, breakeven $354.05, max gain $595). At $345 at expiry: -$750 vs -$405;
at $355: -$250 vs +$95; at $370: +$1,250 vs +$595. Lower risk does not guarantee profit: the spread
still loses its full cost below $350 and caps the gain.

## Technology choices

- Python 3.12 via uv; LangGraph for orchestration; LangChain model integrations.
- LLM switch in `.env` (`LLM_PROVIDER`): `ollama` (`qwen3:8b`, free, for development) or `anthropic`
  (Claude, for testing and the demo).
- Data: yfinance by default behind `MarketDataProvider`; Schwab API added later if approved; Finnhub for news
  and earnings dates.
- Streamlit + Plotly dashboard; SQLite for history.

## Implementation status

- [x] Project setup, data provider (yfinance), options math with tests, starter dashboard
- [x] Wrap data and math functions as agent tools (`agents/tools.py`)
- [x] Options Analysis agent end to end (`agents/options_agent.py`, LangGraph ReAct)
- [x] Retrieval layer: knowledge base + news with MMR (Checkpoint 3)
- [x] Data-quality checks and strategy comparison tool (Checkpoint 2 feedback)
- [ ] Stock, News and Sentiment, Risk agents
- [ ] LangGraph orchestration with shared state, Critic, revision loop (max 2)
- [ ] Report-vs-tool consistency check
- [ ] SQLite long-term memory and comparison with past analyses
- [ ] Report shown in the dashboard
- [ ] Scenario snapshots, answer keys and evaluation harness (with/without Critic)
