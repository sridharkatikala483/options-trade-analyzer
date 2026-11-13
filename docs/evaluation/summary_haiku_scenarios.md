# Evaluation results

Updated 2026-11-13 14:22 · model `claude-haiku-5-5` · 12 contracts · 36 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Required statements missing or wrong | Overconfident sentences | Held for review | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified_tot (first draft) | 12 | 100% | 3 | 0 | 1 | 0 | 0 |  | 98% of 105 | 0 | — | 0.3 | 28 | 20741 / 4877 |
| retrieval_verified_tot (final) | 12 | 100% | 0 | 0 | 0 | 0 | 0 | 0 of 12 | 100% of 104 | 0 | — | 0.3 | 28 | 20741 / 4877 |
| multi_agent (first draft) | 12 | 100% | 3 | 0 | 0 | 0 | 0 |  | 100% of 69 | 0 | 8 in 9 reviews | 0.8 | 65 | 37020 / 15025 |
| multi_agent (final) | 12 | 100% | 0 | 0 | 0 | 0 | 0 | 0 of 12 | 100% of 68 | 0 | 0 in 12 reviews | 0.8 | 65 | 37020 / 15025 |
| multi_agent_rules (first draft) | 12 | 100% | 1 | 0 | 0 | 0 | 2 |  | 98% of 60 | 0 | — | 0.2 | 45 | 19487 / 10068 |
| multi_agent_rules (final) | 12 | 100% | 0 | 0 | 0 | 0 | 0 | 0 of 12 | 100% of 61 | 0 | — | 0.2 | 45 | 19487 / 10068 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| WMT 127 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| HD 337.5 put 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 10 | 0 |
| HD 337.5 put 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 6 | 1 |
| HD 337.5 put 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| PANW 335 call 2026-11-27 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 10 | 0 |
| PANW 335 call 2026-11-27 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| PANW 335 call 2026-11-27 | multi_agent | 100% | 0 | 0 | 0 | 0 of 9 | 1 |
| ZM 99 put 2026-11-27 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 10 | 2 |
| ZM 99 put 2026-11-27 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| ZM 99 put 2026-11-27 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| TSLA 490 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 8 | 0 |
| TSLA 490 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| TSLA 490 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| AAPL 315 put 2026-11-27 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| AAPL 315 put 2026-11-27 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| AAPL 315 put 2026-11-27 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| MSFT 470 call 2026-12-18 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 9 | 0 |
| MSFT 470 call 2026-12-18 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 6 | 0 |
| MSFT 470 call 2026-12-18 | multi_agent | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| F 11 put 2026-12-18 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| F 11 put 2026-12-18 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 3 | 0 |
| F 11 put 2026-12-18 | multi_agent | 100% | 0 | 0 | 0 | 0 of 3 | 1 |
| AMD 560 call 2027-03-19 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| AMD 560 call 2027-03-19 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| AMD 560 call 2027-03-19 | multi_agent | 100% | 0 | 0 | 0 | 0 of 5 | 2 |
| WMT 127 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| SPY 753 call 2026-11-13 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| SPY 753 call 2026-11-13 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| SPY 753 call 2026-11-13 | multi_agent | 100% | 0 | 0 | 0 | 0 of 6 | 0 |
| QQQ 672 put 2026-11-13 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 11 | 0 |
| QQQ 672 put 2026-11-13 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| QQQ 672 put 2026-11-13 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 1 |
| KO 90 put 2027-01-15 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
| KO 90 put 2027-01-15 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 1 |
| KO 90 put 2027-01-15 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
