# Evaluation results

Updated 2026-11-13 14:24 · model `claude-haiku-5-5` · 6 contracts · 18 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Required statements missing or wrong | Overconfident sentences | Held for review | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval_verified_tot (first draft) | 6 | 92% | 1 | 0 | 0 | 0 | 0 |  | 98% of 44 | 0 | — | 0.5 | 31 | 24930 / 5474 |
| retrieval_verified_tot (final) | 6 | 100% | 0 | 0 | 0 | 0 | 0 | 2 of 6 | 100% of 46 | 0 | — | 0.5 | 31 | 24930 / 5474 |
| multi_agent (first draft) | 6 | 97% | 2 | 0 | 0 | 0 | 0 |  | 97% of 33 | 0 | 1 in 3 reviews | 1.2 | 63 | 38380 / 14624 |
| multi_agent (final) | 6 | 97% | 1 | 0 | 0 | 0 | 0 | 4 of 6 | 100% of 33 | 0 | 1 in 5 reviews | 1.2 | 63 | 38380 / 14624 |
| multi_agent_rules (first draft) | 6 | 97% | 3 | 0 | 0 | 0 | 2 |  | 100% of 32 | 0 | — | 0.8 | 50 | 24215 / 10866 |
| multi_agent_rules (final) | 6 | 100% | 1 | 0 | 0 | 2 | 0 | 3 of 6 | 100% of 25 | 0 | — | 0.8 | 50 | 24215 / 10866 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 9 | 1 |
| HD 337.5 put 2026-11-20 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 10 | 1 |
| HD 337.5 put 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| HD 337.5 put 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| SPY 753 call 2026-11-13 | multi_agent_rules | 100% | 1 | 0 | 0 | 0 of 0 | 2 |
| SPY 753 call 2026-11-13 | multi_agent | 83% | 1 | 0 | 0 | 0 of 7 | 2 |
| MSFT 470 call 2026-12-18 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 4 | 0 |
| MSFT 470 call 2026-12-18 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 2 | 1 |
| MSFT 470 call 2026-12-18 | multi_agent | 100% | 0 | 0 | 0 | 0 of 4 | 2 |
| KO 90 put 2027-01-15 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 8 | 0 |
| KO 90 put 2027-01-15 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 6 | 0 |
| KO 90 put 2027-01-15 | multi_agent | 100% | 0 | 0 | 0 | 0 of 3 | 2 |
| AMD 560 call 2027-03-19 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| AMD 560 call 2027-03-19 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 5 | 0 |
| AMD 560 call 2027-03-19 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 0 |
| WMT 127 call 2026-11-20 | multi_agent_rules | 100% | 0 | 0 | 0 | 0 of 7 | 2 |
| WMT 127 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 7 | 1 |
| SPY 753 call 2026-11-13 | retrieval_verified_tot | 100% | 0 | 0 | 0 | 0 of 8 | 1 |
