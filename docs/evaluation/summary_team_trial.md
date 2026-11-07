# Evaluation results

Updated 2026-11-06 23:23 · model `qwen3:8b` · 1 contracts · 1 runs

Scored by the rule-based verifier against each run's own tool outputs. The retrieval_verified
setup is also *revised* by the same verifier, so its final scores show what the loop achieves;
its first-draft scores show the agent before verification.

| Setup | Runs | Tool completeness | Unsupported numbers | Date errors | Liquidity contradictions | Citation accuracy | Recommendations | Avg revisions | Avg seconds | Avg tokens (in/out) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multi_agent (first draft) | 1 | 100% | 0 | 0 | 0 | 100% of 2 | 0 | 0.0 | 655 | 11020 / 4561 |
| multi_agent (final) | 1 | 100% | 0 | 0 | 0 | 100% of 2 | 0 | 0.0 | 655 | 11020 / 4561 |

## Per run

| Contract | Setup | Completeness | Unsupported numbers | Date errors | Liquidity contradictions | Invalid citations | Revisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | multi_agent | 100% | 0 | 0 | 0 | 0 of 2 | 0 |
