# ToT alternative search vs fixed spread

Updated 2026-11-13 20:24 · 12 contracts · same cached market data for every method · proposer model `claude-haiku-5-5`

Every alternative is scored on the ToT scale (100 points; pruned if a leg is illiquid, the maximum loss is not lower than the original, or the score is below 40). A *usable* alternative is one that passes those checks. Max-loss reduction is averaged over the contracts where the method found a usable one.

| Method | Usable alternatives | Avg score (usable) | Avg max-loss reduction | Avg candidates scored |
| --- | --- | --- | --- | --- |
| fixed | 2 of 12 | 66.2 | 75% | 1 |
| beam_rules | 4 of 12 | 72.0 | 75% | 8.0 |
| beam_llm | 4 of 12 | 74.0 | 78% | 7.8 |
| exhaustive | 4 of 12 | 72.0 | 75% | 29.2 |

## Head to head

- Fixed spread unusable (pruned or missing): 10 of 12; ToT (rules) found a usable alternative in 4 of 12.
- Where both were usable (2): ToT scored higher in 2, had a lower maximum loss in 2.
- Beam (rules) matched the exhaustive best score in 12 of 12, scoring 96 candidates vs 351 for exhaustive search.
- LLM proposer vs rules (4 comparable): higher score in 2, equal in 2, lower in 0; 0 of 32 proposals fell back to defaults; 7 s per search on average.

## Per contract (strategy · expiration · max loss · score)

| Contract | Original max loss | fixed | beam_rules | beam_llm | exhaustive |
| --- | --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | $440 | bull call spread 127/131 11-20 · $178 · 72.0 | bull call spread 127/130 11-20 · $135 · 77.1 | bull put spread 127/125 11-20 · $113 · 82.9 | bull call spread 127/130 11-20 · $135 · 77.1 |
| HD 337.5 put 2026-11-20 | $445 | bear put spread 337.5/327.5 11-20 · $234 · 42.6 · **pruned: a leg has poor liquidity** | bear put spread 337.5/330 11-20 · $186 · 52.9 | bear put spread 337.5/330 11-20 · $186 · 52.9 | bear put spread 337.5/330 11-20 · $186 · 52.9 |
| PANW 335 call 2026-11-27 | $1,395 | bull call spread 335/345 11-27 · $312 · 53.4 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity, score below 40) | none (no qualifying alternative: a leg has poor liquidity, score below 40) | none (every candidate pruned) |
| ZM 99 put 2026-11-27 | $558 | bear put spread 99/96 11-27 · $140 · 62.1 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| SPY 753 call 2026-11-13 | $72 | bull call spread 753/763 11-13 · $70 · 33.8 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: maximum loss is not lower than the original, a leg has poor liquidity) | none (no qualifying alternative: maximum loss is not lower than the original, a leg has poor liquidity) | none (every candidate pruned) |
| QQQ 672 put 2026-11-13 | $20 | bear put spread 672/652 11-13 · $18 · 26.1 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: maximum loss is not lower than the original, a leg has poor liquidity) | none (no qualifying alternative: maximum loss is not lower than the original, a leg has poor liquidity) | none (every candidate pruned) |
| TSLA 490 call 2026-11-20 | $4 | bull call spread 490/500 11-20 · $-0 · 84.0 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| AAPL 315 put 2026-11-27 | $26 | bear put spread 315/305 11-27 · $8 · 29.1 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| MSFT 470 call 2026-12-18 | $5,932 | bull call spread 470/485 12-18 · $1,292 · 78.0 · **pruned: a leg has poor liquidity** | bull put spread 470/455 01-15 · $1,305 · 84.2 | bull put spread 470/460 01-15 · $858 · 86.5 | bull put spread 470/455 01-15 · $1,305 · 84.2 |
| KO 90 put 2027-01-15 | $64 | bear put spread 90/87.5 01-15 · $26 · 34.5 · **pruned: chance beyond breakeven below 15%** | none (no qualifying alternative: chance beyond breakeven below 15%, maximum loss is not lower than the original, a leg has poor liquidity) | none (no qualifying alternative: chance beyond breakeven below 15%, a leg has poor liquidity) | none (every candidate pruned) |
| F 11 put 2026-12-18 | $14 | bear put spread 11/10 12-18 · $10 · 17.9 · **pruned: a leg has poor liquidity** | none (no qualifying alternative: a leg has poor liquidity, maximum loss is not lower than the original) | none (no qualifying alternative: a leg has poor liquidity) | none (every candidate pruned) |
| AMD 560 call 2027-03-19 | $6,548 | bull call spread 560/580 03-19 · $665 · 60.3 | bull put spread 560/550 03-19 · $302 · 73.6 | bull put spread 560/550 03-19 · $302 · 73.6 | bull put spread 560/550 03-19 · $302 · 73.6 |

## Risk-adjusted comparison

Is the pick better, or only a smaller maximum loss? Each figure is per $100 of that position's own maximum loss, so a $300 spread and an $800 call compare fairly. *Past moves*: every overlapping window of the stock's last 2y with the same number of trading days to expiration, applied to today's price. *Black-Scholes*: the distribution the option prices imply (drift = risk-free rate, the legs' average implied volatility). Only its chance of profit is shown: its expected profit is about zero by construction, and what remains measures how one shared volatility misprices legs with different implied volatilities, not an edge. Bid-ask is the round trip (open and close) versus the mid-quote. `original` is averaged over the contracts where ToT (rules) found a usable alternative; each method over its own usable picks.

| Position | Contracts | Max gain per $1 risked | Expected P/L, past moves | Chance of profit, past moves | Chance of profit, Black-Scholes | Bid-ask round trip | IV −40% | IV +20% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original | 4 | unlimited | +$35.6 | 35% | 33% | $4.0 | -$38.7 | +$20.7 |
| fixed | 2 | 1.63 | +$55.2 | 60% | 40% | $44.7 | -$5.1 | +$0.1 |
| beam_rules | 4 | 1.68 | +$22.6 | 56% | 48% | $63.5 | -$7.9 | +$1.3 |
| beam_llm | 4 | 1.57 | +$27.5 | 60% | 51% | $63.4 | -$4.3 | +$0.4 |
| exhaustive | 4 | 1.68 | +$22.6 | 56% | 48% | $63.5 | -$7.9 | +$1.3 |

### Per contract (dollars per one set of contracts)

| Contract | Position | Picked by | Max loss | Max gain | Expected P/L, past moves | Chance, past moves | Chance, Black-Scholes | Bid-ask round trip | IV −40% | IV +20% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | original 127 11-20 | original | $440 | unlimited | -$203 | 21% | 34% | $10 | -$161 | +$80 |
| WMT 127 call 2026-11-20 | bull call spread 127/131 11-20 | fixed | $178 | $222 | -$8 | 46% | 44% | $20 | -$15 | +$4 |
| WMT 127 call 2026-11-20 | bull call spread 127/130 11-20 | beam_rules, exhaustive | $135 | $165 | +$8 | 51% | 45% | $20 | -$6 | +$1 |
| WMT 127 call 2026-11-20 | bull put spread 127/125 11-20 | beam_llm | $113 | $87 | +$29 | 70% | 55% | $14 | +$10 | -$3 |
| HD 337.5 put 2026-11-20 | original 337.5 11-20 | original | $445 | $33,305 | -$353 | 8% | 24% | $20 | -$282 | +$158 |
| HD 337.5 put 2026-11-20 | bear put spread 337.5/327.5 11-20 | fixed (pruned) | $234 | $766 | -$156 | 11% | 28% | $37 | -$116 | +$38 |
| HD 337.5 put 2026-11-20 | bear put spread 337.5/330 11-20 | beam_rules, beam_llm, exhaustive | $186 | $564 | -$116 | 12% | 28% | $40 | -$86 | +$27 |
| PANW 335 call 2026-11-27 | original 335 11-27 | original | $1,395 | unlimited | -$667 | 17% | 27% | $200 | -$742 | +$381 |
| PANW 335 call 2026-11-27 | bull call spread 335/345 11-27 | fixed (pruned) | $312 | $688 | -$41 | 29% | 34% | $285 | -$64 | +$13 |
| ZM 99 put 2026-11-27 | original 99 11-27 | original | $558 | $9,342 | -$317 | 15% | 36% | $115 | -$225 | +$112 |
| ZM 99 put 2026-11-27 | bear put spread 99/96 11-27 | fixed (pruned) | $140 | $160 | -$21 | 41% | 48% | $220 | -$13 | +$4 |
| SPY 753 call 2026-11-13 | original 753 11-13 | original | $72 | unlimited | +$225 | 51% | 34% | $1 | -$15 | +$8 |
| SPY 753 call 2026-11-13 | bull call spread 753/763 11-13 | fixed (pruned) | $70 | $930 | +$188 | 51% | 42% | $2 | -$15 | +$8 |
| QQQ 672 put 2026-11-13 | original 672 11-13 | original | $20 | $67,180 | +$101 | 17% | 2% | $1 | -$3 | +$6 |
| QQQ 672 put 2026-11-13 | bear put spread 672/652 11-13 | fixed (pruned) | $18 | $1,982 | +$93 | 17% | 10% | $2 | -$3 | +$6 |
| TSLA 490 call 2026-11-20 | original 490 11-20 | original | $4 | unlimited | -$1 | 1% | 0% | $2 | -$3 | +$12 |
| TSLA 490 call 2026-11-20 | bull call spread 490/500 11-20 | fixed (pruned) | $-0 | $1,000 | +$3 | 100% | 100% | $3 | +$0 | -$1 |
| AAPL 315 put 2026-11-27 | original 315 11-27 | original | $26 | $31,474 | -$11 | 1% | 3% | $3 | -$24 | +$40 |
| AAPL 315 put 2026-11-27 | bear put spread 315/305 11-27 | fixed (pruned) | $8 | $992 | +$0 | 1% | 4% | $8 | -$6 | +$5 |
| MSFT 470 call 2026-12-18 | original 470 12-18 | original | $5,932 | unlimited | +$472 | 45% | 46% | $175 | -$429 | +$311 |
| MSFT 470 call 2026-12-18 | bull call spread 470/485 12-18 | fixed (pruned) | $1,292 | $208 | +$54 | 88% | 76% | $335 | +$107 | -$28 |
| MSFT 470 call 2026-12-18 | bull put spread 470/455 01-15 | beam_rules, exhaustive | $1,305 | $195 | +$6 | 86% | 80% | $100 | +$112 | -$37 |
| MSFT 470 call 2026-12-18 | bull put spread 470/460 01-15 | beam_llm | $858 | $142 | +$8 | 85% | 80% | $85 | +$84 | -$28 |
| KO 90 put 2027-01-15 | original 90 01-15 | original | $64 | $8,936 | -$64 | 0% | 12% | $4 | -$50 | +$41 |
| KO 90 put 2027-01-15 | bear put spread 90/87.5 01-15 | fixed (pruned) | $26 | $224 | -$26 | 0% | 14% | $10 | -$18 | +$8 |
| F 11 put 2026-12-18 | original 11 12-18 | original | $14 | $1,086 | -$5 | 14% | 19% | $2 | -$11 | +$7 |
| F 11 put 2026-12-18 | bear put spread 11/10 12-18 | fixed (pruned) | $10 | $90 | -$2 | 15% | 21% | $3 | -$8 | +$3 |
| AMD 560 call 2027-03-19 | original 560 03-19 | original | $6,548 | unlimited | +$17,019 | 67% | 27% | $405 | -$3,123 | +$1,555 |
| AMD 560 call 2027-03-19 | bull call spread 560/580 03-19 | fixed | $665 | $1,335 | +$764 | 73% | 37% | $520 | -$13 | -$14 |
| AMD 560 call 2027-03-19 | bull put spread 560/550 03-19 | beam_rules, beam_llm, exhaustive | $302 | $698 | +$443 | 74% | 40% | $635 | +$31 | -$21 |

Scores and probabilities are Black-Scholes estimates on mid-quotes, not forecasts; a lower maximum loss does not guarantee a profit. Education only.
