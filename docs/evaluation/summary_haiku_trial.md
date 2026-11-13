# Evaluation results

Updated 2026-11-07 23:06 · model `claude-haiku-5-5` · 1 contracts · 1 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Citation accuracy | Recommendations | Judgment issues (LLM Critic) | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multi_agent (first draft) | 1 | 100% | 0 | 0 | 0 | 83% of 6 | 0 | — | 1.0 | 74 | 33112 / 14714 |
| multi_agent (final) | 1 | 100% | 0 | 0 | 0 | 100% of 6 | 0 | 0 in 1 reviews | 1.0 | 74 | 33112 / 14714 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 6 | 1 |
