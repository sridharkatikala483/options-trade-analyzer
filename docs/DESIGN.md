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

Revised in Checkpoint 5 (multi-agent architecture): five LLM agents plus a Coordinator in plain code.
Stock Analysis merged into Market Context (trend takes 1-2 tool calls and answers the same question as the
news); the Orchestrator became code (its decisions are fixed rules); a Writer was split from the Critic.

| Agent | Responsibility | Tools |
| --- | --- | --- |
| Coordinator (code) | Validates input, loads one market snapshot for all agents, routing, round limits, failover | data provider (retry, fallback) |
| Options Analyst | Price vs model, Greeks, liquidity, quote freshness, implied volatility | contract + data-quality tool, Greeks calculator, knowledge search |
| Market Context | Trend, key levels, earnings date, recent headlines | price history, earnings calendar, news search, knowledge search |
| Risk Strategist | Max loss, breakeven, volatility-drop scenario, lower-risk alternative | payoff calculator, ToT alternative search, risk-adjusted measures |
| Writer | One report built only from the three findings | none (reads state) |
| Critic | Rule checks (verifier) first, then an LLM review of judgment and conflicts; targeted revision requests to the owning agent, max 2 rounds | verifier, reads all findings |

Coordination (hybrid graph): Coordinator -> Options Analyst and Market Context in parallel -> join ->
Risk Strategist -> Writer -> Critic -> (revision to the owning agent, max 2 rounds) -> report. Agents
communicate only through shared typed state: one-way handoffs along the pipeline, two-way Critic validation,
brainstorming only inside the ToT search. Findings are structured claims with their tool evidence and a
confidence level. Conditional edges: no earnings before expiry skips the volatility-drop scenario; a failed
data source is retried, replaced, then marked low confidence.

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

## Tree-of-Thought alternative search — Checkpoint 4

ToT is used for one part of the agent only: finding a lower-risk alternative. Fact gathering stays
the verified ReAct loop (one correct result per step, so branching would add cost without accuracy).
`search_alternatives` (`agents/tot_search.py`, scoring in `analytics/alternatives.py`) replaces the fixed
one-spread `compare_strategies` when `analyze_contract(..., use_tot=True)`; both stay for comparison.

| ToT question | Choice |
| --- | --- |
| Thought | One narrowing decision: strategy family (depth 1), strikes (depth 2), expiration (depth 3) |
| Generator | LLM via `get_llm()` proposes from a menu of listed strikes/expirations (propose, not sample); off-menu replies are discarded and invalid replies fall back to default choices (`TOT_PROPOSER=rules` skips the LLM) |
| Evaluator | Deterministic Python score out of 100: risk reduction 30 (maximum loss plus the bid-ask cost to open, since Checkpoint 4 feedback), breakeven distance 25, chance beyond breakeven (Black-Scholes) 20, exposure to a 40% IV drop 15, worst-leg liquidity 10 |
| Search | Beam search, width 3, depth 3, as a LangGraph loop (generate -> evaluate -> select); the tree (parent, legs, score, pruning reason) lives in the graph state |

- Families: call -> bull call spread, bull put spread, cheaper (further OTM) call; put -> bear put spread,
  bear call spread, cheaper put. Spreads keep the original strike as one leg. Strike menu: listed strikes
  1.5-12.5% of the stock price beyond it (defaults 2.5/5/7.5/10%); expiration menu: the original plus up to
  2 later ones within 60 days. Partial nodes are scored by their best completion over the default strikes and
  *every* expiration on the menu (lookahead). The first version completed them at the original expiration
  only, so a thin original expiration pruned every family at depth 1; the evaluation below found this.
- Pruning (objective only): a leg with poor liquidity or no two-sided quote, maximum loss not lower than
  the original, a Black-Scholes chance beyond breakeven below 15% (a "lottery ticket": added after the
  risk-adjusted evaluation found a 2% SPY call scoring 62), or score below 40. Ties within 2 points go to lower max loss, better liquidity, fewer legs.
- Diversity: the beam keeps each surviving family's best node first at every level. (The design said
  depth 1, but a family has one node there; crowding happens at depth 2, where it has several strikes.)
- Limits: at most 24 scored nodes, 3 option chains, about 7 proposal calls, 900 s time limit (best so far).
- Output: the original, the selected position and a runner-up (cost, max loss/gain, breakevens, payoffs,
  chance, IV-drop change, liquidity, score and points), pruning reasons, LLM calls and fallbacks. If every
  branch is pruned, the outcome is "no qualifying alternative" with the reasons. The verifier requires the
  tool when `use_tot` and accepts the selected position's expiration as a valid date.
- Risk check: `exhaustive()` scores every default path; on the test chain the beam finds the exhaustive best.
- Example (live, 2026-11-01, rule proposer): AAPL 345 call to Nov 20 (max loss $1,047.50) -> bull put spread
  345/337.5, max loss $445, credit $305, score 78.1; runner-up bull call spread 345/352.5, max loss $372.50.
  A thin Wednesday weekly (Nov 11) first returned "no qualifying alternative"; with the lookahead fix the
  search moves to the liquid Nov 20 expiration instead.

### Evaluation: ToT vs the fixed spread (`scripts/evaluate_tot.py`, results in `docs/evaluation/tot_summary.md`)

Same 10 contracts as the agent evaluation, same cached market data for every method, all scored on the
ToT scale. "Usable" = passes the pruning checks. Run 2026-11-01, qwen3:8b proposer with thinking off.

| Method | Usable | Avg score | Avg max-loss cut | Candidates scored |
| --- | --- | --- | --- | --- |
| Fixed spread (`compare_strategies`) | 0 of 10 | — | — | 1 |
| ToT beam, rule proposer | 7 of 10 | 63.5 | 55% | 13.7 |
| ToT beam, LLM proposer | 7 of 10 | 67.7 | 69% | 12.1 |
| Exhaustive (default menus) | 7 of 10 | 63.5 | 55% | 32.6 |

- The fixed spread always lowered the maximum loss, but 9 of 10 used a poorly traded leg (it is locked to
  the original, often thin weekly, expiration and never checks liquidity) and 1 scored below 40.
- The beam matched the exhaustive best in 10 of 10 while scoring 42% of the candidates. Before the
  lookahead fix it matched in only 4 of 10 and found usable alternatives in 2 of 10.
- The LLM proposer beat the rules in 5 of 7, tied 1, lost 1, with 0 of 41 fallbacks, 26 s per search.
  It can beat "exhaustive" because it picks from the full 8-step strike menu (often narrower spreads),
  while exhaustive only covers the 4 default steps.
- No method found a usable alternative for KO, AMD or F: every candidate had a thin leg or too low a
  score, and the tool says so instead of forcing a pick.
- Full agent with and without ToT (`evaluate.py --setups retrieval_verified,retrieval_verified_tot --out tot`,
  `docs/evaluation/summary_tot.md`, 10 contracts, 2026-11-02): first drafts with ToT used every required
  tool (100% vs 81%) and had 9 unsupported numbers vs 25, with 1.0 revisions vs 1.5; final reports were
  equal (1 unsupported number each), 0 recommendations in all 20 runs, 13.7 vs 13.2 minutes per run,
  ~60% more input tokens. One ToT final report (F) still called a "good" liquidity rating poor.
  Recommendation quality needs a judgment-based review (rubric, later the LLM Critic).

## Validation loop (from instructor feedback on Checkpoint 3)

`agents/verifier.py` checks every final report against the tool outputs of the same run; failures go back
to the agent as a revision request, at most 2 rounds (`analyze_contract(..., verify_report=True)`).
This is the deterministic first stage of the Critic; an LLM Critic for judgment calls comes later.

| Check | Rule |
| --- | --- |
| Tool-use completeness | contract, Greeks, earnings date, strategy comparison (+ knowledge and news search with retrieval); the volatility-drop scenario is required when earnings fall on or before expiry |
| Number consistency | every number in the report must appear in a tool result (rounding allowed; small counts <= 12 ignored) |
| Dates | only dates the tools returned (earnings, expiry, quote time, news) |
| Liquidity wording | "wide spread", "illiquid", "low volume/open interest" are rejected when the rating is good |
| Citations | `[KB: id]` must be a passage retrieved in this run; `[News: ...]` must match a returned headline source |
| No advice | recommendation phrasing is rejected |

The prompt also states explicit tool-use conditions (IF earnings before expiry THEN run the
iv_change_pct=-40 scenario; use only compare_strategies numbers for the alternative).

**Measuring retrieval and validation** (`scripts/evaluate.py` -> `docs/evaluation/`): 10 varied contracts
(calls/puts, 7-45 days, at/out of the money, earnings before expiry or not, an ETF, thin and liquid
contracts) x 3 setups (`no_retrieval`, `retrieval`, `retrieval_verified`), scored on tool completeness,
unsupported numbers, date errors, liquidity contradictions (general guidance misapplied), citation
accuracy, recommendations, revisions, runtime and tokens. Market data and headlines are cached per
contract so setups are compared on identical inputs. Caveat: the verified setup is revised by the same
checks that score it, so its first-draft scores are reported too, and reports are spot-checked by hand.

**Results (qwen3:8b, 30 runs, 2026-10-30/31; full tables in `docs/evaluation/summary.md`):**

| Setup | Tool completeness | Unsupported numbers | Citation accuracy | Avg revisions | Avg seconds |
| --- | --- | --- | --- | --- | --- |
| no_retrieval | 96% | 11 | n/a | 0 | 336 |
| retrieval | 79% | 17 | 92% of 40 | 0 | 303 |
| retrieval_verified, first draft | 79% | 24 | 91% of 44 | - | - |
| retrieval_verified, final | 100% | 3 | 89% of 45 | 1.5 | 818 |

- Retrieval alone lowered quality: the agent skipped required tools and added more unsupported numbers
  while citing sources, i.e. more credibility without more accuracy.
- The verifier loop restored completeness (100%) and cut unsupported numbers from 24 to 3, at about 2.7x
  the runtime and 3-4x the input tokens. Invalid citations are flagged but often not fixed (89%).
- Hand spot-check (JPM 320 put) found errors the rules cannot catch: "deeply out-of-the-money" for a
  5% OTM strike, a self-computed difference that passed only by coincidental match with another tool
  number, and a "no relevant news" line next to a news citation. These motivate the LLM Critic.
- Runner fixes from the run: a 600 s Ollama request timeout (a dropped connection hung one run for
  hours) and resume reuses already-started contracts (re-resolving on a later day changed SPY's expiry).

## Evaluation: single agent vs team, with and without the LLM Critic (Checkpoint 5)

Snapshot `data/snapshots/2026-11-06.json.gz`, 10 contracts x 3 setups, qwen3:8b; verifier results in
`docs/evaluation/summary_compare.md`, answer-key scores in `docs/evaluation/quality_compare.md`
(`scripts/score_reports.py`, keys in `data/answer_keys/`).

| | Single agent (ToT + retrieval + verifier) | Team, rule Critic only | Team + LLM Critic |
| --- | --- | --- | --- |
| Final reports passing every rule check | 9 of 10 (1 date error) | 8 of 10 (4 untraced numbers) | 10 of 10 |
| First-draft problems | 7 untraced numbers, 3 liquidity, 1 date | 9 untraced numbers | 3 untraced numbers |
| Average revision rounds | 1.3 | 1.0 | 0.5 |
| Answer-key facts stated | 77% | 85% | 82% |
| Answer-key mistakes (reports clean) | 3 (7 of 10) | 3 (7 of 10) | 2 (8 of 10) |
| Average minutes per run | 16 | 21 | 21 (excluding one 7.7 h looping run) |
| Average input tokens per run | 30,400 | 16,600 | 20,000 |

- The team with the LLM Critic is the most reliable: every final report passed and first drafts needed the
  fewest fixes. Both teams state more answer-key facts than the single agent, with smaller contexts per agent.
- Gaps shared by all setups: Black-Scholes vs American-style limits missing (6-7 reports each; about 2 are
  wordings the matcher misses), earnings after expiry listed as a risk (2-3 each by the matcher; a hand check
  found about 4 real cases in all, the rest correct sentences such as "crush occurs only if earnings are before
  expiry"); the single agent often omits "lower risk does not guarantee a profit" (8 of 10).
- Fix (after the run): both prompts now give the two required sentences a fixed place (end of Lower-risk
  alternative, start of Limits), and the rule verifier rejects a report missing either one (`statement_issues`,
  routed to the Writer). On the 30 reports it would have sent back 25. Earnings after expiry stays with the LLM
  Critic (check 2 made more specific): a word rule flagged about as many correct sentences as mistakes.
- The rule-Critic-only team cited sources rarely (4 citations in 10 reports vs 12 and 35).
- Runner fix from the run: qwen3 occasionally loops in its thinking; with tokens still streaming the 600 s
  timeout never fires (one call ran 4+ hours past 100,000 tokens). `get_llm` now caps each reply at 8,192
  tokens (`num_predict`); a whole normal run outputs under 13,000 tokens.

## Re-run on Claude Haiku with the Checkpoint 6 guardrails

Same snapshot and 10 contracts x 3 setups, `claude-haiku-5-5`, every guardrail on (results
`docs/evaluation/summary_haiku_compare.md`, `quality_haiku_compare.md`).

| | Single agent | Team, rule Critic only | Team + LLM Critic |
| --- | --- | --- | --- |
| Final reports passing every rule check | 10 of 10 | 10 of 10 | 10 of 10 |
| Held for review | 0 | 0 | 0 |
| Answer-key facts stated | 100% | 98% | 98% |
| Answer-key mistakes | 0 | 1 flagged, a matcher false positive on hand check | 0 |
| Average revision rounds | 0.2 | 0.6 | 0.5 |
| Average seconds per run | 33 | 49 | 57 |
| Average tokens per run (in / out) | 18,900 / 4,700 | 22,100 / 10,100 | 31,100 / 12,300 |

- On a stronger model the single agent is as good as the team and faster and cheaper: the team's gains on
  qwen3:8b (fewer untraced numbers, more facts) came from making up for a weak model. The team stays useful for
  its structure (ownership, routing, parallel specialists) but is not needed for quality on Haiku.
- Two answer-key items (model limits, "does not guarantee a profit") are now also enforced by the verifier, so
  part of the 98-100% is by design rather than independent evidence.
- The run found a verifier bug: the advice check matched Haiku's disclaimer "This report does not recommend
  buying, selling, or any position size", so 7 of 30 first drafts were rejected and 4 runs ended held for
  review. `recommends()` now ignores a match with a negation just before it (tests added); the 7 runs were
  re-run. qwen3 never wrote that disclaimer, which is why the bug did not show before.
- Every run is "shown with a warning" because every recorded quote is from a closed market.
- Cost: about 721,000 input and 271,000 output tokens for the 30 runs.

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
- [x] Specialists split per the Checkpoint 5 design (`agents/team.py`): Options Analyst, Market Context
      (+ `get_price_trend`, `analytics/trend.py`), Risk Strategist, Writer; coordinator in code
- [x] LangGraph orchestration: shared state, parallel specialists + join, rule-based Critic, fixes routed
      to the owning agent, revision loop (max 2); `evaluate.py` setup `multi_agent`
- [x] LLM Critic (`agents/critic.py`): judgment review with a 7-point checklist, only after the rule checks
      pass; names the owning agent; unreadable replies count as no issues. On the trial report it found a
      misused number the rules missed (a 13.8 score figure presented as the volatility-drop reduction;
      the evidence shows -313.59 -> -25.56). qwen3 thinking stays on (9.4 min; thinking off: 24 s but a
      wrong review). `evaluate.py` setups `multi_agent` (with) vs `multi_agent_rules` (without)
- [x] Report-vs-tool consistency check + completeness check + revision loop (`agents/verifier.py`)
- [x] Evaluation harness for retrieval and validation (`scripts/evaluate.py`)
- [x] Run the full evaluation (10 contracts x 3 setups) and record results
- [x] Tree-of-Thought lower-risk alternative search (`search_alternatives`, `use_tot`, Checkpoint 4)
- [x] Evaluate ToT vs fixed-spread alternative on the evaluation contracts (beam vs exhaustive; lookahead fix)
- [x] ToT report quality end to end (`evaluate.py` setup with `use_tot`): accuracy, compliance, latency
- [x] Risk-adjusted comparison of the picks (Checkpoint 4 feedback; `analytics/risk_metrics.py`,
      `docs/evaluation/tot_summary_risk.md`); score fix: 15% chance floor + bid-ask cost in risk points
      (same data scored both ways: `tot_summary_scored_checkpoint4.md` vs `tot_summary_scored.md`)
- [ ] LLM vs rule proposer on a larger, more diverse contract set (Checkpoint 4 feedback)
- [ ] Recommendation-quality rubric for the with/without-ToT reports (Checkpoint 4 feedback)
- [ ] SQLite long-term memory and comparison with past analyses
- [x] Report shown in the dashboard (`app.py`): "Run AI analysis" runs the team with live per-agent progress;
      report, each agent's findings and tool calls, the Critic's checks (first draft vs final) and fixes sent,
      run time and tokens; the selected alternative drawn on the payoff chart; with DATA_PROVIDER=snapshot the
      sidebar offers the recorded contracts. The run is a background job (`jobs.py`): a reload or click does
      not cancel it, progress refreshes every 3 s with a "now working on" line, one run at a time
- [x] Market-data snapshots (`data/snapshot.py`, `scripts/record_snapshot.py`, `clock.py`): record the 10
      evaluation contracts once (quotes, chains the ToT search can visit, earnings, 6m/2y history, headlines;
      0.3 MB), replay with `DATA_PROVIDER=snapshot`, clock frozen at the recording time. Two replays of
      `evaluate_tot.py --no-llm` gave identical results. First snapshot: `data/snapshots/2026-11-06.json.gz`
- [x] Answer keys built from the snapshot (`answer_keys.py`, `scripts/score_reports.py`) and the comparison:
      single agent vs team, with and without the LLM Critic (results above)
- [x] Fix for the shared gaps: required sentences in both prompts, a rule check for them, a sharper Critic
      earnings check
- [x] Repeat the comparison with the Checkpoint 6 guardrails on Claude Haiku (results above; found and fixed the
      negated-advice false positive)
- [x] Checkpoint 6 guardrails, part 1: overconfidence check in the rule verifier (certainty words, skipped when
      the sentence hedges; on the 30 saved reports it flags the one real case, "No risk (earnings are after
      expiration)", and nothing else; known gap: "guaranteed if ..." passes, left to Critic check 4) and input
      risk flags computed by code (`analytics/input_risk.py`: 2 days or fewer, poor liquidity, closed-market
      quote, under 15% risk-neutral chance beyond breakeven), shown above the report and given to the Writer.
      The snapshot has no short-expiry or low-chance contract (closest: F at 16.7%), so those two are tested on
      synthetic contracts only
- [x] Checkpoint 6 part 2: outcomes, run log and review queue (`review.py`). Code decides each run's outcome
      (shown / shown with a warning / held for review / refused) from the checks; every dashboard run is appended
      to `data/runs/runs.jsonl` (gitignored) with its trace; reviewer decisions (approved / edited / rejected,
      with a note) go to `reviews.jsonl`, never over the run. Dashboard: "Review queue" page, outcome banners, a
      held draft hidden until approved. Escalation on the 30 saved runs: 5 of 30 (17%, target 20% or less);
      the team with the LLM Critic held 2 of 10, both because qwen3's Critic reply had no JSON. Timestamps use
      `clock.wall_now()` (a replay freezes market time, not review time). Not covered: a fallback-data trigger
      (no fallback signal exists yet) and refusal for the single agent (only the team reports an invalid request)
- [x] Injection monitor for headlines (`injection.py`, `scripts/injection_eval.py` -> `docs/evaluation/injection.md`):
      every fresh headline is scanned before the agents see it; a flagged one is withheld (source, date and
      reason only) and the run is held for review; prompts frame headlines as information, never instructions.
      Results: 14 of 14 direct injections caught, 0 false alarms in 914 recorded headlines. Paraphrases: tuning
      raised the tuning set from 0 to 6 of 6 but a held-out set written beforehand only from 0 to 1 of 6, so
      word patterns overfit and plain-language attacks rely on the other layers (output checks, Critic)
- [x] Week 5 feedback, part 1: scenario snapshot (`data/snapshots/2026-11-13-scenarios.json.gz`, `--specs
      scenarios`): 12 contracts recorded during market hours covering earnings before expiry (5), expiring today
      (2), very low chance (4), deep in the money, long-dated, fresh and delayed quotes, 6 puts, and a real missing
      earnings date (KO, F)
- [x] Week 5 feedback, part 2: acceptance gate (`acceptance.py`; a pass/fail table in every
      `quality_<name>.md` from `score_reports.py`): tool completeness 100%, 0 untraced numbers, dates or
      citations, 0 recommendations, at most 1 judgment error per 10 reports (answer-key mistakes minus flags a
      person ruled out in `data/answer_keys/hand_checks.json`, each with a note), at least 90% of required facts,
      at most 20% held for review, at most 120 s per run. Haiku passes every threshold in all three setups;
      qwen3:8b fails on facts (77-85%) and time (16-65 min), so it stays the free development model
- [x] Week 5 feedback, part 3a: exposure check for alternatives. The search now rejects an alternative that
      does not move with the stock the way the original does, or whose maximum loss plus the bid-ask cost to open
      is not lower (the rule used mid prices before), or that shows no loss at mid prices (a quote artifact: the
      scenario snapshot found a TSLA bull put spread whose credit equalled its strike width, which also crashed
      the chance formula with a $0 breakeven). `alternatives.trade_offs()` lists how the selected alternative's
      exposure differs (capped gain, a short leg that can be assigned, a credit, a different expiration, a chance
      5+ points lower); the search output carries the list, the prompts ask for it, and the verifier sends back a
      report that leaves one out. On the saved reports, assignment risk was missing in 19 of 20 Haiku and 20 of
      21 qwen3 reports with a spread; qwen3 also left out the capped gain in 17 of 21
- [x] Week 5 feedback, part 3b: missing-data cases (`scripts/make_missing_data_snapshot.py` ->
      `data/snapshots/2026-11-13-missing.json.gz`, `--specs missing`): six scenario contracts with one gap each
      (blank implied volatility, no price history, no headlines, later chains not loaded, no bid or ask, no
      earnings date). They found four failures, now fixed: a blank IV flowed on as NaN and crashed the
      alternative search; a failed history call raised instead of returning an error; one unloadable chain
      crashed the search; no bid or ask went unflagged (with a meaningless 3.7% IV). Now the contract tool lists
      `data_quality.missing`, every tool turns a failed source into {"error": "data unavailable ..."}, the search
      skips an expiration it cannot load, and missing data or a failed source holds the run for review
- [x] Hand-scoring rubric for judgment errors (`docs/evaluation/hand_scoring.md`): procedure, seven
      categories with examples from our runs, severity, borderline rules; decisions go to
      `data/answer_keys/hand_checks.json`
- [ ] Haiku run on the scenario and missing-data sets
