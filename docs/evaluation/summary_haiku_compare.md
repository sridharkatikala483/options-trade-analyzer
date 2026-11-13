# Evaluation results

Updated 2026-11-13 12:31 · model `claude-haiku-5-5` · 10 contracts · 30 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Required statements missing or wrong | Overconfident sentences | Held for review | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified_tot (first draft) | 10 | 100% | 1 | 0 | 1 | 0 | 1 |  | 100% of 81 | 0 | — | 0.2 | 33 | 18889 / 4677 |
| retrieval_verified_tot (final) | 10 | 100% | 0 | 0 | 0 | 0 | 0 | 0 of 10 | 100% of 81 | 0 | — | 0.2 | 33 | 18889 / 4677 |
| multi_agent (first draft) | 10 | 100% | 4 | 0 | 0 | 0 | 0 |  | 98% of 56 | 0 | 1 in 6 reviews | 0.5 | 57 | 31076 / 12283 |
| multi_agent (final) | 10 | 100% | 0 | 0 | 0 | 0 | 0 | 0 of 10 | 100% of 59 | 0 | 0 in 10 reviews | 0.5 | 57 | 31076 / 12283 |
| multi_agent_rules (first draft) | 10 | 100% | 3 | 0 | 0 | 0 | 1 |  | 93% of 56 | 0 | — | 0.6 | 49 | 22131 / 10137 |
| multi_agent_rules (final) | 10 | 100% | 0 | 0 | 0 | 0 | 0 | 0 of 10 | 100% of 65 | 0 | — | 0.6 | 49 | 22131 / 10137 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 2 | 0 |
| AAPL 342.5 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| AAPL 342.5 put 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| AAPL 342.5 put 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| AAPL 342.5 put 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 3 | 0 |
| MSFT 555 call 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 12 | 0 |
| MSFT 555 call 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| MSFT 555 call 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| NVDA 185 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 10 | 0 |
| NVDA 185 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| TSLA 340 put 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| TSLA 340 put 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| KO 96 call 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 11 | 1 |
| AMD 495 call 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| AMD 495 call 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 6 | 1 |
| SPY 735 call 2026-11-13 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 6 | 0 |
| SPY 735 call 2026-11-13 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| SPY 735 call 2026-11-13 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| F 14 call 2027-01-15 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| F 14 call 2027-01-15 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| JPM 320 put 2026-12-11 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| JPM 320 put 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 6 | 1 |
| JPM 320 put 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 9 | 1 |
| AAPL 342.5 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| NVDA 185 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| TSLA 340 put 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| KO 96 call 2026-12-11 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 10 | 0 |
| KO 96 call 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| AMD 495 call 2026-12-11 | multi_agent | 100% | 0 | 0 | 0 | 0 of 6 | 1 |
| F 14 call 2027-01-15 | multi_agent | 100% | 0 | 0 | 0 | 0 of 6 | 0 |
