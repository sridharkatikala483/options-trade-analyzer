# Report quality against answer keys: haiku_scenarios

Updated 2026-11-13 14:24 · snapshot `data/snapshots/2026-11-13-scenarios.json.gz` · 36 reports

Each report is checked against its contract's answer key: facts a correct report must state, and mistakes it must not make (built from the snapshot with the project's tools; plain text and number matching, so spot-check unusual wordings).

| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |
| --- | --- | --- | --- | --- | --- |
| multi_agent_rules | 12 | 103 of 103 (100%) | 12 | 0 | 12 |
| multi_agent | 12 | 101 of 103 (98%) | 10 | 0 | 12 |
| retrieval_verified_tot | 12 | 102 of 103 (99%) | 11 | 0 | 12 |

## Acceptance gate

Thresholds from `acceptance.py` (Week 5 feedback). Judgment errors count answer-key mistakes not ruled out by hand in `data/answer_keys/hand_checks.json` (0 ruled out for this file).

| Threshold | Target | multi_agent_rules | multi_agent | retrieval_verified_tot |
| --- | --- | --- | --- | --- |
| Required tools used (final reports) | >= 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| Numbers, dates or citations no tool returned (final reports) | <= 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| Reports that recommend a trade or size | <= 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| Judgment errors per 10 reports (answer-key mistakes not ruled out by hand) | <= 1.0 | ✅ 0.0 | ✅ 0.0 | ✅ 0.0 |
| Required facts stated (answer keys) | >= 90% | ✅ 100% | ✅ 98% | ✅ 99% |
| Runs held for human review | <= 20% | ✅ 0% | ✅ 0% | ✅ 0% |
| Average seconds per run (target set for a hosted model) | <= 120 | ✅ 45 | ✅ 65 | ✅ 28 |
| **All thresholds** | | **pass** | **pass** | **pass** |

## Most often missed or wrong

| Setup | Item | Reports |
| --- | --- | --- |
| multi_agent | Says how many days are left (when 14 or fewer) | 1 |
| multi_agent | Says earnings fall after expiry | 1 |
| retrieval_verified_tot | Says how many days are left (when 14 or fewer) | 1 |

## Per report

| Contract | Setup | Facts met | Missing | Mistakes |
| --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | multi_agent_rules | 9 of 9 | — | — |
| WMT 127 call 2026-11-20 | multi_agent | 9 of 9 | — | — |
| HD 337.5 put 2026-11-20 | retrieval_verified_tot | 9 of 9 | — | — |
| HD 337.5 put 2026-11-20 | multi_agent_rules | 9 of 9 | — | — |
| HD 337.5 put 2026-11-20 | multi_agent | 9 of 9 | — | — |
| PANW 335 call 2026-11-27 | retrieval_verified_tot | 9 of 9 | — | — |
| PANW 335 call 2026-11-27 | multi_agent_rules | 9 of 9 | — | — |
| PANW 335 call 2026-11-27 | multi_agent | 8 of 9 | days_left | — |
| ZM 99 put 2026-11-27 | retrieval_verified_tot | 9 of 9 | — | — |
| ZM 99 put 2026-11-27 | multi_agent_rules | 9 of 9 | — | — |
| ZM 99 put 2026-11-27 | multi_agent | 9 of 9 | — | — |
| TSLA 490 call 2026-11-20 | retrieval_verified_tot | 9 of 9 | — | — |
| TSLA 490 call 2026-11-20 | multi_agent_rules | 9 of 9 | — | — |
| TSLA 490 call 2026-11-20 | multi_agent | 8 of 9 | earnings_after | — |
| AAPL 315 put 2026-11-27 | retrieval_verified_tot | 9 of 9 | — | — |
| AAPL 315 put 2026-11-27 | multi_agent_rules | 9 of 9 | — | — |
| AAPL 315 put 2026-11-27 | multi_agent | 9 of 9 | — | — |
| MSFT 470 call 2026-12-18 | retrieval_verified_tot | 10 of 10 | — | — |
| MSFT 470 call 2026-12-18 | multi_agent_rules | 10 of 10 | — | — |
| MSFT 470 call 2026-12-18 | multi_agent | 10 of 10 | — | — |
| F 11 put 2026-12-18 | retrieval_verified_tot | 7 of 7 | — | — |
| F 11 put 2026-12-18 | multi_agent_rules | 7 of 7 | — | — |
| F 11 put 2026-12-18 | multi_agent | 7 of 7 | — | — |
| AMD 560 call 2027-03-19 | retrieval_verified_tot | 8 of 8 | — | — |
| AMD 560 call 2027-03-19 | multi_agent_rules | 8 of 8 | — | — |
| AMD 560 call 2027-03-19 | multi_agent | 8 of 8 | — | — |
| WMT 127 call 2026-11-20 | retrieval_verified_tot | 9 of 9 | — | — |
| SPY 753 call 2026-11-13 | retrieval_verified_tot | 8 of 8 | — | — |
| SPY 753 call 2026-11-13 | multi_agent_rules | 8 of 8 | — | — |
| SPY 753 call 2026-11-13 | multi_agent | 8 of 8 | — | — |
| QQQ 672 put 2026-11-13 | retrieval_verified_tot | 7 of 8 | days_left | — |
| QQQ 672 put 2026-11-13 | multi_agent_rules | 8 of 8 | — | — |
| QQQ 672 put 2026-11-13 | multi_agent | 8 of 8 | — | — |
| KO 90 put 2027-01-15 | retrieval_verified_tot | 8 of 8 | — | — |
| KO 90 put 2027-01-15 | multi_agent_rules | 8 of 8 | — | — |
| KO 90 put 2027-01-15 | multi_agent | 8 of 8 | — | — |
