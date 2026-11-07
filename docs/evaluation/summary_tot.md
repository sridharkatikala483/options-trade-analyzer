# Evaluation results

Updated 2026-11-02 01:22 · model `qwen3:8b` · 10 contracts · 20 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Citation accuracy | Recommendations | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified (first draft) | 10 | 81% | 25 | 0 | 1 | 94% of 34 | 0 | 1.5 | 794 | 17488 / 5471 |
| retrieval_verified (final) | 10 | 100% | 1 | 0 | 0 | 100% of 47 | 0 | 1.5 | 794 | 17488 / 5471 |
| retrieval_verified_tot (first draft) | 10 | 100% | 9 | 0 | 1 | 88% of 33 | 0 | 1.0 | 819 | 28635 / 5394 |
| retrieval_verified_tot (final) | 10 | 100% | 1 | 0 | 1 | 100% of 33 | 0 | 1.0 | 819 | 28635 / 5394 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 345 call 2026-11-11 | retrieval_verified | 100% | 1 | 0 | 0 | 0 of 4 | 2 |
| AAPL 345 call 2026-11-11 | retrieval_verified_tot | 100% | 1 | 0 | 0 | 0 of 5 | 2 |
| AAPL 345 put 2026-11-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 5 | 2 |
| AAPL 345 put 2026-11-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| MSFT 550 call 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 6 | 1 |
| MSFT 550 call 2026-12-04 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| NVDA 205 call 2026-11-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| NVDA 205 call 2026-11-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| TSLA 380 put 2026-11-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| TSLA 380 put 2026-11-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| KO 94 call 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| KO 94 call 2026-12-04 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 2 |
| AMD 555 call 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 6 | 2 |
| AMD 555 call 2026-12-04 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 0 |
| SPY 755 call 2026-11-09 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 4 | 2 |
| SPY 755 call 2026-11-09 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| F 14 call 2026-12-18 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 3 | 2 |
| F 14 call 2026-12-18 | retrieval_verified_tot | 100% | 0 | 0 | 1 | 0 of 1 | 2 |
| JPM 320 put 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| JPM 320 put 2026-12-04 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 1 | 0 |
