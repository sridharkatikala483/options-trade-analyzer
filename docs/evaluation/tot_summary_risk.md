# ToT alternative search vs fixed spread

Updated 2026-11-06 22:07 · 10 contracts · same cached market data for every method · proposer model `qwen3:8b`

Every alternative is scored on the ToT scale (100 points; pruned if a leg is illiquid, the maximum loss is not lower than the original, or the score is below 40). A *usable* alternative is one that passes those checks. Max-loss reduction is averaged over the contracts where the method found a usable one.

| Method | Usable alternatives | Avg score (usable) | Avg max-loss reduction | Avg candidates scored |
| --- | --- | --- | --- | --- |
| fixed | 5 of 10 | 65.0 | 52% | 1 |
| beam_rules | 7 of 10 | 66.2 | 64% | 13.9 |
| beam_llm | 7 of 10 | 69.0 | 67% | 11.2 |
| exhaustive | 7 of 10 | 66.2 | 64% | 28.7 |

## Head to head

- Fixed spread unusable (pruned or missing): 5 of 10; ToT (rules) found a usable alternative in 7 of 10.
- Where both were usable (5): ToT scored higher in 5, had a lower maximum loss in 2.
- Beam (rules) matched the exhaustive best score in 10 of 10, scoring 139 candidates vs 287 for exhaustive search.
- LLM proposer vs rules (7 comparable): higher score in 4, equal in 2, lower in 1; 0 of 43 proposals fell back to defaults; 21 s per search on average.

## Per contract (strategy · expiration · max loss · score)

| Contract | Original max loss | fixed | beam_rules | beam_llm | exhaustive |
| --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | $752 | bull call spread 342.5/352.5 11-20 · $440 · 63.4 | bull put spread 342.5/335 11-20 · $475 · 72.2 | bull call spread 342.5/347.5 11-20 · $248 · 75.9 | bull put spread 342.5/335 11-20 · $475 · 72.2 |
| AAPL 342.5 put 2026-11-20 | $740 | bear put spread 342.5/332.5 11-20 · $340 · 70.7 | bear put spread 342.5/335 11-20 · $275 · 74.9 | bear put spread 342.5/337.5 11-20 · $195 · 79.8 | bear put spread 342.5/335 11-20 · $275 · 74.9 |
| MSFT 555 call 2026-12-11 | $940 | bull call spread 555/570 12-11 · $420 · 44.4 · **pruned: a leg has poor liquidity** | bull call spread 555/570 12-18 · $435 · 54.7 | bull call spread 555/570 12-18 · $435 · 54.7 | bull call spread 555/570 12-18 · $435 · 54.7 |
| NVDA 185 call 2026-11-20 | $1,142 | bull call spread 185/190 11-20 · $260 · 80.8 | bull put spread 185/180 12-04 · $290 · 82.9 | bull put spread 185/180 12-04 · $290 · 82.9 | bull put spread 185/180 12-04 · $290 · 82.9 |
| TSLA 340 put 2026-11-20 | $890 | bear put spread 340/330 11-20 · $242 · 61.8 | bear call spread 340/350 11-27 · $312 · 64.1 | bear put spread 340/330 11-20 · $242 · 61.8 | bear call spread 340/350 11-27 · $312 · 64.1 |
| KO 96 call 2026-12-11 | $232 | bull call spread 96/99 12-11 · $114 · 57.4 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| AMD 495 call 2026-12-11 | $1,915 | bull call spread 495/510 12-11 · $412 · 42.1 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity, score below 40) | none (no qualifying alternative: a leg has poor liquidity, score below 40) | none (every candidate pruned) |
| SPY 735 call 2026-11-13 | $1,025 | bull call spread 735/757 11-13 · $890 · 48.3 | cheaper call 772 11-13 · $11 · 62.1 | bull call spread 735/746 11-13 · $560 · 66.7 | cheaper call 772 11-13 · $11 · 62.1 |
| F 14 call 2027-01-15 | $18 | bull call spread 14/14.85 01-15 · $9 · 32.9 · **pruned: score below 40** | none (no qualifying alternative: score below 40, maximum loss is not lower than the original) | none (no qualifying alternative: score below 40, maximum loss is not lower than the original) | none (every candidate pruned) |
| JPM 320 put 2026-12-11 | $430 | bear put spread 320/310 12-11 · $144 · 49.7 · **pruned: a leg has poor liquidity** | bear put spread 320/310 12-18 · $182 · 52.2 | bear put spread 320/315 12-18 · $92 · 61.1 | bear put spread 320/310 12-18 · $182 · 52.2 |

## Risk-adjusted comparison

Is the pick better, or only a smaller maximum loss? Each figure is per $100 of that position's own maximum loss, so a $300 spread and an $800 call compare fairly. *Past moves*: every overlapping window of the stock's last 2y with the same number of trading days to expiration, applied to today's price. *Black-Scholes*: the distribution the option prices imply (drift = risk-free rate, the legs' average implied volatility). Only its chance of profit is shown: its expected profit is about zero by construction, and what remains measures how one shared volatility misprices legs with different implied volatilities, not an edge. Bid-ask is the round trip (open and close) versus the mid-quote. `original` is averaged over the contracts where ToT (rules) found a usable alternative; each method over its own usable picks.

| Position | Contracts | Max gain per $1 risked | Expected P/L, past moves | Chance of profit, past moves | Chance of profit, Black-Scholes | Bid-ask round trip | IV −40% | IV +20% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original | 7 | unlimited | -$17.7 | 25% | 31% | $11.2 | -$54.1 | +$28.6 |
| fixed | 5 | 1.74 | -$10.4 | 37% | 40% | $8.1 | -$19.8 | +$5.7 |
| beam_rules | 7 | unlimited | +$2.7 | 36% | 37% | $30.5 | -$35.0 | +$41.0 |
| beam_llm | 7 | 2.03 | -$5.2 | 38% | 40% | $31.5 | -$21.1 | +$5.7 |
| exhaustive | 7 | unlimited | +$2.7 | 36% | 37% | $30.5 | -$35.0 | +$41.0 |

### Per contract (dollars per one set of contracts)

| Contract | Position | Picked by | Max loss | Max gain | Expected P/L, past moves | Chance, past moves | Chance, Black-Scholes | Bid-ask round trip | IV −40% | IV +20% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | original 342.5 11-20 | original | $752 | unlimited | +$138 | 43% | 35% | $25 | -$314 | +$157 |
| AAPL 342.5 call 2026-11-20 | bull call spread 342.5/352.5 11-20 | fixed | $440 | $560 | +$41 | 50% | 41% | $40 | -$82 | +$27 |
| AAPL 342.5 call 2026-11-20 | bull put spread 342.5/335 11-20 | beam_rules, exhaustive | $475 | $275 | +$31 | 66% | 55% | $40 | +$20 | -$1 |
| AAPL 342.5 call 2026-11-20 | bull call spread 342.5/347.5 11-20 | beam_llm | $248 | $252 | +$19 | 54% | 45% | $45 | -$26 | +$9 |
| AAPL 342.5 put 2026-11-20 | original 342.5 11-20 | original | $740 | $33,510 | -$181 | 26% | 35% | $20 | -$302 | +$151 |
| AAPL 342.5 put 2026-11-20 | bear put spread 342.5/332.5 11-20 | fixed | $340 | $660 | -$37 | 33% | 44% | $40 | -$35 | +$3 |
| AAPL 342.5 put 2026-11-20 | bear put spread 342.5/335 11-20 | beam_rules, exhaustive | $275 | $475 | -$31 | 34% | 45% | $40 | -$20 | +$1 |
| AAPL 342.5 put 2026-11-20 | bear put spread 342.5/337.5 11-20 | beam_llm | $195 | $305 | -$19 | 37% | 46% | $40 | -$6 | -$1 |
| MSFT 555 call 2026-12-11 | original 555 12-11 | original | $940 | unlimited | +$430 | 26% | 26% | $210 | -$701 | +$378 |
| MSFT 555 call 2026-12-11 | bull call spread 555/570 12-11 | fixed (pruned) | $420 | $1,080 | -$21 | 29% | 28% | $340 | -$207 | +$68 |
| MSFT 555 call 2026-12-11 | bull call spread 555/570 12-18 | beam_rules, beam_llm, exhaustive | $435 | $1,065 | +$9 | 31% | 30% | $100 | -$173 | +$52 |
| NVDA 185 call 2026-11-20 | original 185 11-20 | original | $1,142 | unlimited | -$441 | 25% | 34% | $5 | -$428 | +$214 |
| NVDA 185 call 2026-11-20 | bull call spread 185/190 11-20 | fixed | $260 | $240 | -$9 | 50% | 46% | $10 | -$10 | +$4 |
| NVDA 185 call 2026-11-20 | bull put spread 185/180 12-04 | beam_rules, beam_llm, exhaustive | $290 | $210 | +$41 | 65% | 52% | $50 | +$15 | -$3 |
| TSLA 340 put 2026-11-20 | original 340 11-20 | original | $890 | $33,110 | -$324 | 18% | 27% | $20 | -$566 | +$307 |
| TSLA 340 put 2026-11-20 | bear put spread 340/330 11-20 | fixed, beam_llm | $242 | $758 | -$34 | 23% | 33% | $35 | -$85 | +$20 |
| TSLA 340 put 2026-11-20 | bear call spread 340/350 11-27 | beam_rules, exhaustive | $312 | $688 | +$28 | 36% | 43% | $215 | -$36 | +$2 |
| KO 96 call 2026-12-11 | original 96 12-11 | original | $232 | unlimited | +$43 | 38% | 36% | $55 | -$111 | +$55 |
| KO 96 call 2026-12-11 | bull call spread 96/99 12-11 | fixed (pruned) | $114 | $186 | +$21 | 47% | 42% | $90 | -$18 | +$5 |
| AMD 495 call 2026-12-11 | original 495 12-11 | original | $1,915 | unlimited | +$2,384 | 36% | 23% | $160 | -$1,270 | +$691 |
| AMD 495 call 2026-12-11 | bull call spread 495/510 12-11 | fixed (pruned) | $412 | $1,088 | +$155 | 39% | 27% | $335 | -$154 | +$43 |
| SPY 735 call 2026-11-13 | original 735 11-13 | original | $1,025 | unlimited | -$350 | 25% | 36% | $8 | -$419 | +$210 |
| SPY 735 call 2026-11-13 | bull call spread 735/757 11-13 | fixed | $890 | $1,310 | -$290 | 30% | 36% | $13 | -$279 | +$104 |
| SPY 735 call 2026-11-13 | cheaper call 772 11-13 | beam_rules, exhaustive | $11 | unlimited | +$3 | 2% | 2% | $2 | -$16 | +$29 |
| SPY 735 call 2026-11-13 | bull call spread 735/746 11-13 | beam_llm | $560 | $540 | -$110 | 40% | 42% | $15 | -$98 | +$37 |
| F 14 call 2027-01-15 | original 14 01-15 | original | $18 | unlimited | -$1 | 17% | 17% | $3 | -$17 | +$11 |
| F 14 call 2027-01-15 | bull call spread 14/14.85 01-15 | fixed (pruned) | $9 | $76 | +$1 | 18% | 18% | $4 | -$7 | +$3 |
| JPM 320 put 2026-12-11 | original 320 12-11 | original | $430 | $31,570 | -$234 | 11% | 25% | $200 | -$342 | +$195 |
| JPM 320 put 2026-12-11 | bear put spread 320/310 12-11 | fixed (pruned) | $144 | $856 | -$38 | 16% | 29% | $267 | -$96 | +$27 |
| JPM 320 put 2026-12-11 | bear put spread 320/310 12-18 | beam_rules, exhaustive | $182 | $818 | -$52 | 16% | 29% | $115 | -$87 | +$22 |
| JPM 320 put 2026-12-11 | bear put spread 320/315 12-18 | beam_llm | $92 | $408 | -$16 | 18% | 30% | $115 | -$43 | +$11 |

Scores and probabilities are Black-Scholes estimates on mid-quotes, not forecasts; a lower maximum loss does not guarantee a profit. Education only.
