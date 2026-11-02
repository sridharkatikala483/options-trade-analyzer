# ToT alternative search vs fixed spread

Updated 2026-11-01 20:46 · 10 contracts · same cached market data for every method · proposer model `qwen3:8b`

Every alternative is scored on the ToT scale (100 points; pruned if a leg is illiquid, the maximum loss is not lower than the original, or the score is below 40). A *usable* alternative is one that passes those checks. Max-loss reduction is averaged over the contracts where the method found a usable one.

| Method | Usable alternatives | Avg score (usable) | Avg max-loss reduction | Avg candidates scored |
| --- | --- | --- | --- | --- |
| fixed | 0 of 10 | 0.0 | 0% | 1 |
| beam_rules | 7 of 10 | 63.5 | 55% | 13.7 |
| beam_llm | 7 of 10 | 67.7 | 69% | 12.1 |
| exhaustive | 7 of 10 | 63.5 | 55% | 32.6 |

## Head to head

- Fixed spread unusable (pruned or missing): 10 of 10; ToT (rules) found a usable alternative in 7 of 10.
- Where both were usable (0): ToT scored higher in 0, had a lower maximum loss in 0.
- Beam (rules) matched the exhaustive best score in 10 of 10, scoring 137 candidates vs 326 for exhaustive search.
- LLM proposer vs rules (7 comparable): higher score in 5, equal in 1, lower in 1; 0 of 41 proposals fell back to defaults; 26 s per search on average.

## Per contract (strategy · expiration · max loss · score)

| Contract | Original max loss | fixed | beam_rules | beam_llm | exhaustive |
| --- | --- | --- | --- | --- | --- |
| AAPL 345 call 2026-11-11 | $882 | bull call spread 345/355 11-11 · $455 · 56.4 · **pruned: a leg has poor liquidity** | bull put spread 345/337.5 11-20 · $445 · 75.6 | bull put spread 345/340 11-20 · $295 · 80.4 | bull put spread 345/337.5 11-20 · $445 · 75.6 |
| AAPL 345 put 2026-11-11 | $845 | bear put spread 345/335 11-11 · $332 · 64.1 · **pruned: a leg has poor liquidity** | bear put spread 345/337.5 11-20 · $305 · 76.2 | bear put spread 345/340 11-13 · $200 · 80.9 | bear put spread 345/337.5 11-20 · $305 · 76.2 |
| MSFT 550 call 2026-12-04 | $682 | bull call spread 550/565 12-04 · $288 · 43.7 · **pruned: a leg has poor liquidity** | bull call spread 550/565 12-18 · $382 · 44.8 | bull call spread 550/565 12-18 · $382 · 44.8 | bull call spread 550/565 12-18 · $382 · 44.8 |
| NVDA 205 call 2026-11-11 | $575 | bull call spread 205/210 11-11 · $228 · 61.4 · **pruned: a leg has poor liquidity** | bull put spread 205/200 11-20 · $282 · 75.6 | bull put spread 205/202.5 11-13 · $138 · 83.0 | bull put spread 205/200 11-20 · $282 · 75.6 |
| TSLA 380 put 2026-11-11 | $540 | bear put spread 380/367.5 11-11 · $238 · 43.5 · **pruned: a leg has poor liquidity** | bear call spread 380/390 11-13 · $312 · 58.3 | bear put spread 380/370 11-13 · $220 · 55.6 | bear call spread 380/390 11-13 · $312 · 58.3 |
| KO 94 call 2026-12-04 | $232 | bull call spread 94/97 12-04 · $124 · 56.8 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| AMD 555 call 2026-12-04 | $2,050 | bull call spread 555/570 12-04 · $442 · 42.0 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| SPY 755 call 2026-11-09 | $918 | bull call spread 755/780 11-09 · $868 · 33.6 · **pruned: a leg has poor liquidity** | cheaper call 775 11-09 · $114 · 67.3 | cheaper call 780 11-10 · $70 · 67.9 | cheaper call 775 11-09 · $114 · 67.3 |
| F 14 call 2026-12-18 | $10 | bull call spread 14/14.67 12-18 · $5 · 32.4 · **pruned: score below 40** | none (no qualifying alternative: score below 40, maximum loss is not lower than the original, a leg has poor liquidity) | none (no qualifying alternative: score below 40, maximum loss is not lower than the original, a leg has poor liquidity) | none (every candidate pruned) |
| JPM 320 put 2026-12-04 | $375 | bear put spread 320/310 12-04 · $169 · 42.5 · **pruned: a leg has poor liquidity** | bear put spread 320/310 12-18 · $187 · 46.6 | bear put spread 320/315 12-18 · $108 · 61.1 | bear put spread 320/310 12-18 · $187 · 46.6 |

Scores and probabilities are Black-Scholes estimates on mid-quotes, not forecasts; a lower maximum loss does not guarantee a profit. Education only.
