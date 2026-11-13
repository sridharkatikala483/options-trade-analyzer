# Evaluation results

Updated 2026-11-08 23:34 · model `qwen3:8b` · 10 contracts · 30 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified_tot (first draft) | 10 | 97% | 7 | 1 | 3 | 88% of 25 | 0 | — | 1.3 | 968 | 30374 / 6064 |
| retrieval_verified_tot (final) | 10 | 100% | 0 | 1 | 0 | 100% of 35 | 0 | — | 1.3 | 968 | 30374 / 6064 |
| multi_agent (first draft) | 10 | 100% | 3 | 0 | 0 | 100% of 12 | 0 | 1 in 7 reviews | 0.5 | 3894 | 19975 / 25108 |
| multi_agent (final) | 10 | 100% | 0 | 0 | 0 | 100% of 12 | 0 | 0 in 10 reviews | 0.5 | 3894 | 19975 / 25108 |
| multi_agent_rules (first draft) | 10 | 100% | 9 | 0 | 0 | 100% of 4 | 0 | — | 1.0 | 1236 | 16594 / 8804 |
| multi_agent_rules (final) | 10 | 100% | 4 | 0 | 0 | 100% of 4 | 0 | — | 1.0 | 1236 | 16594 / 8804 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 1 |
| AAPL 342.5 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 2 |
| AAPL 342.5 put 2026-11-20 | retrieval_verified_tot | 100% | 0 | 1 | 0 | 0 of 3 | 2 |
| AAPL 342.5 put 2026-11-20 | multi_agent_rules | 100% | 2 | 0 | 0 | 0 of 0 | 2 |
| AAPL 342.5 put 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 2 | 0 |
| MSFT 555 call 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 2 |
| MSFT 555 call 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 1 |
| MSFT 555 call 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| NVDA 185 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| NVDA 185 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 1 |
| NVDA 185 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| TSLA 340 put 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 2 |
| TSLA 340 put 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| TSLA 340 put 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| KO 96 call 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| KO 96 call 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| KO 96 call 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 1 | 1 |
| AMD 495 call 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| AAPL 342.5 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 2 |
| AMD 495 call 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 2 |
| AMD 495 call 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 0 | 1 |
| SPY 735 call 2026-11-13 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| SPY 735 call 2026-11-13 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| SPY 735 call 2026-11-13 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| F 14 call 2027-01-15 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| F 14 call 2027-01-15 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| F 14 call 2027-01-15 | multi_agent | 100% | 0 | 0 | 0 | 0 of 0 | 0 |
| JPM 320 put 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| JPM 320 put 2026-12-11 | multi_agent_rules | 100% | 2 | 0 | 0 | 0 of 0 | 2 |
| JPM 320 put 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 1 | 1 |
