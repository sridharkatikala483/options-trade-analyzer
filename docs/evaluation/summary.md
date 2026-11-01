# Evaluation results

Updated 2026-10-31 10:12 · model `qwen3:8b` · 10 contracts · 30 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Citation accuracy | Recommendations | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_retrieval | 10 | 96% | 11 | 0 | 0 | n/a | 0 | 0.0 | 336 | 5678 / 2355 |
| retrieval | 10 | 79% | 17 | 0 | 1 | 92% of 40 | 0 | 0.0 | 303 | 4442 / 2111 |
| retrieval_verified (first draft) | 10 | 79% | 24 | 0 | 1 | 91% of 44 | 0 | 1.5 | 818 | 16893 / 5069 |
| retrieval_verified (final) | 10 | 100% | 3 | 0 | 1 | 89% of 45 | 0 | 1.5 | 818 | 16893 / 5069 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 345 call 2026-11-13 | no_retrieval | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| AAPL 345 call 2026-11-13 | retrieval | 71% | 1 | 0 | 0 | 0 of 4 | 0 |
| AAPL 345 call 2026-11-13 | retrieval_verified | 100% | 1 | 0 | 0 | 2 of 6 | 2 |
| AAPL 345 put 2026-11-13 | no_retrieval | 80% | 2 | 0 | 0 | 0 of 0 | 0 |
| AAPL 345 put 2026-11-13 | retrieval | 71% | 2 | 0 | 0 | 0 of 4 | 0 |
| AAPL 345 put 2026-11-13 | retrieval_verified | 100% | 2 | 0 | 1 | 0 of 5 | 2 |
| MSFT 550 call 2026-12-04 | no_retrieval | 100% | 2 | 0 | 0 | 0 of 0 | 0 |
| MSFT 550 call 2026-12-04 | retrieval | 83% | 1 | 0 | 0 | 1 of 4 | 0 |
| MSFT 550 call 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 2 of 5 | 2 |
| NVDA 205 call 2026-11-13 | no_retrieval | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| NVDA 205 call 2026-11-13 | retrieval | 83% | 5 | 0 | 0 | 1 of 4 | 0 |
| NVDA 205 call 2026-11-13 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 5 | 2 |
| TSLA 380 put 2026-11-13 | no_retrieval | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| TSLA 380 put 2026-11-13 | retrieval | 83% | 3 | 0 | 0 | 0 of 4 | 0 |
| TSLA 380 put 2026-11-13 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| KO 94 call 2026-12-04 | no_retrieval | 100% | 1 | 0 | 0 | 0 of 0 | 0 |
| KO 94 call 2026-12-04 | retrieval | 83% | 1 | 0 | 0 | 1 of 5 | 0 |
| KO 94 call 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| AMD 555 call 2026-12-04 | no_retrieval | 80% | 3 | 0 | 0 | 0 of 0 | 0 |
| AMD 555 call 2026-12-04 | retrieval | 71% | 1 | 0 | 0 | 0 of 5 | 0 |
| AMD 555 call 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| SPY 756 call 2026-11-06 | no_retrieval | 100% | 1 | 0 | 0 | 0 of 0 | 0 |
| SPY 756 call 2026-11-06 | retrieval | 83% | 2 | 0 | 0 | 0 of 3 | 0 |
| SPY 756 call 2026-11-06 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| F 14 call 2026-12-18 | no_retrieval | 100% | 2 | 0 | 0 | 0 of 0 | 0 |
| F 14 call 2026-12-18 | retrieval | 83% | 0 | 0 | 1 | 0 of 3 | 0 |
| F 14 call 2026-12-18 | retrieval_verified | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| JPM 320 put 2026-12-04 | no_retrieval | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| JPM 320 put 2026-12-04 | retrieval | 83% | 1 | 0 | 0 | 0 of 4 | 0 |
| JPM 320 put 2026-12-04 | retrieval_verified | 100% | 0 | 0 | 0 | 1 of 5 | 2 |
