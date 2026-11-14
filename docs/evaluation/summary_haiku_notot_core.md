# Evaluation results

Updated 2026-11-13 20:29 · model `claude-haiku-5-5` · 10 contracts · 10 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Required statements missing or wrong | Overconfident sentences | Held for review | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified (first draft) | 10 | 100% | 1 | 1 | 0 | 0 | 0 |  | 94% of 82 | 0 | — | 0.6 | 23 | 22022 / 5205 |
| retrieval_verified (final) | 10 | 100% | 0 | 1 | 0 | 0 | 0 | 1 of 10 | 100% of 83 | 0 | — | 0.6 | 23 | 22022 / 5205 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | retrieval_verified | 100% | 0 | 1 | 0 | 0 of 9 | 2 |
| AAPL 342.5 put 2026-11-20 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| MSFT 555 call 2026-12-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 11 | 0 |
| NVDA 185 call 2026-11-20 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 2 |
| TSLA 340 put 2026-11-20 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| KO 96 call 2026-12-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| AMD 495 call 2026-12-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| SPY 735 call 2026-11-13 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| F 14 call 2027-01-15 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 1 |
| JPM 320 put 2026-12-11 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
