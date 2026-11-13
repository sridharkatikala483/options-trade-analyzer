# Report quality against answer keys: haiku_missing

Updated 2026-11-13 14:24 · snapshot `data/snapshots/2026-11-13-missing.json.gz` · 18 reports

Each report is checked against its contract's answer key: facts a correct report must state, and mistakes it must not make (built from the snapshot with the project's tools; plain text and number matching, so spot-check unusual wordings).

| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |
| --- | --- | --- | --- | --- | --- |
| retrieval_verified_tot | 6 | 52 of 52 (100%) | 6 | 0 | 6 |
| multi_agent_rules | 6 | 47 of 52 (90%) | 4 | 0 | 6 |
| multi_agent | 6 | 52 of 52 (100%) | 6 | 0 | 6 |

## Acceptance gate

Thresholds from `acceptance.py` (Week 5 feedback). Judgment errors count answer-key mistakes not ruled out by hand in `data/answer_keys/hand_checks.json` (0 ruled out for this file).

| Threshold | Target | retrieval_verified_tot | multi_agent_rules | multi_agent |
| --- | --- | --- | --- | --- |
| Required tools used (final reports) | >= 100% | ✅ 100% | ✅ 100% | ❌ 97% |
| Numbers, dates or citations no tool returned (final reports) | <= 0 | ✅ 0 | ❌ 1 | ❌ 1 |
| Reports that recommend a trade or size | <= 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| Judgment errors per 10 reports (answer-key mistakes not ruled out by hand) | <= 1.0 | ✅ 0.0 | ✅ 0.0 | ✅ 0.0 |
| Required facts stated (answer keys) | >= 90% | ✅ 100% | ✅ 90% | ✅ 100% |
| Runs held for human review | <= 20% | ❌ 33% | ❌ 50% | ❌ 67% |
| Average seconds per run (target set for a hosted model) | <= 120 | ✅ 31 | ✅ 50 | ✅ 63 |
| **All thresholds** | | **fail** | **fail** | **fail** |

## Most often missed or wrong

| Setup | Item | Reports |
| --- | --- | --- |
| multi_agent_rules | Says how many days are left (when 14 or fewer) | 2 |
| multi_agent_rules | Explains time decay (theta) | 1 |
| multi_agent_rules | Says Black-Scholes only approximates American-style options | 1 |
| multi_agent_rules | Says lower risk does not guarantee a profit | 1 |

## Per report

| Contract | Setup | Facts met | Missing | Mistakes |
| --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | retrieval_verified_tot | 9 of 9 | — | — |
| HD 337.5 put 2026-11-20 | retrieval_verified_tot | 9 of 9 | — | — |
| HD 337.5 put 2026-11-20 | multi_agent_rules | 8 of 9 | days_left | — |
| HD 337.5 put 2026-11-20 | multi_agent | 9 of 9 | — | — |
| SPY 753 call 2026-11-13 | multi_agent_rules | 4 of 8 | time_decay, model_limits, no_guarantee, days_left | — |
| SPY 753 call 2026-11-13 | multi_agent | 8 of 8 | — | — |
| MSFT 470 call 2026-12-18 | retrieval_verified_tot | 10 of 10 | — | — |
| MSFT 470 call 2026-12-18 | multi_agent_rules | 10 of 10 | — | — |
| MSFT 470 call 2026-12-18 | multi_agent | 10 of 10 | — | — |
| KO 90 put 2027-01-15 | retrieval_verified_tot | 8 of 8 | — | — |
| KO 90 put 2027-01-15 | multi_agent_rules | 8 of 8 | — | — |
| KO 90 put 2027-01-15 | multi_agent | 8 of 8 | — | — |
| AMD 560 call 2027-03-19 | retrieval_verified_tot | 8 of 8 | — | — |
| AMD 560 call 2027-03-19 | multi_agent_rules | 8 of 8 | — | — |
| AMD 560 call 2027-03-19 | multi_agent | 8 of 8 | — | — |
| WMT 127 call 2026-11-20 | multi_agent_rules | 9 of 9 | — | — |
| WMT 127 call 2026-11-20 | multi_agent | 9 of 9 | — | — |
| SPY 753 call 2026-11-13 | retrieval_verified_tot | 8 of 8 | — | — |
