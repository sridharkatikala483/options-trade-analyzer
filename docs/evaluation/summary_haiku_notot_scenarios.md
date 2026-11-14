# Evaluation results

Updated 2026-11-13 20:33 · model `claude-haiku-5-5` · 12 contracts · 12 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Required statements missing or wrong | Overconfident sentences | Held for review | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified (first draft) | 12 | 100% | 1 | 1 | 4 | 0 | 0 |  | 99% of 96 | 0 | — | 0.5 | 22 | 20490 / 5006 |
| retrieval_verified (final) | 12 | 100% | 0 | 1 | 0 | 0 | 0 | 1 of 12 | 100% of 102 | 0 | — | 0.5 | 22 | 20490 / 5006 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| HD 337.5 put 2026-11-20 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| PANW 335 call 2026-11-27 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| ZM 99 put 2026-11-27 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| SPY 753 call 2026-11-13 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| QQQ 672 put 2026-11-13 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 10 | 1 |
| TSLA 490 call 2026-11-20 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 8 | 0 |
| AAPL 315 put 2026-11-27 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| MSFT 470 call 2026-12-18 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| KO 90 put 2027-01-15 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| F 11 put 2026-12-18 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| AMD 560 call 2027-03-19 | retrieval_verified | 100% | 0 | 1 | 0 | 0 of 11 | 2 |
