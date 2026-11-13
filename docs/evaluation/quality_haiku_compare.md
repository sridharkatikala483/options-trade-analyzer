# Report quality against answer keys: haiku_compare

Updated 2026-11-13 12:56 · snapshot `data/snapshots/2026-11-06.json.gz` · 30 reports

Each report is checked against its contract's answer key: facts a correct report must state, and mistakes it must not make (built from the snapshot with the project's tools; plain text and number matching, so spot-check unusual wordings).

| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |
| --- | --- | --- | --- | --- | --- |
| retrieval_verified_tot | 10 | 99 of 99 (100%) | 10 | 0 | 10 |
| multi_agent | 10 | 97 of 99 (98%) | 8 | 0 | 10 |
| multi_agent_rules | 10 | 97 of 99 (98%) | 8 | 1 | 9 |

## Acceptance gate

Thresholds from `acceptance.py` (Week 5 feedback). Judgment errors count answer-key mistakes not ruled out by hand in `data/answer_keys/hand_checks.json` (1 ruled out for this file).

| Threshold | Target | retrieval_verified_tot | multi_agent | multi_agent_rules |
| --- | --- | --- | --- | --- |
| Required tools used (final reports) | >= 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| Numbers, dates or citations no tool returned (final reports) | <= 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| Reports that recommend a trade or size | <= 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| Judgment errors per 10 reports (answer-key mistakes not ruled out by hand) | <= 1.0 | ✅ 0.0 | ✅ 0.0 | ✅ 0.0 |
| Required facts stated (answer keys) | >= 90% | ✅ 100% | ✅ 98% | ✅ 98% |
| Runs held for human review | <= 20% | ✅ 0% | ✅ 0% | ✅ 0% |
| Average seconds per run (target set for a hosted model) | <= 120 | ✅ 33 | ✅ 57 | ✅ 49 |
| **All thresholds** | | **pass** | **pass** | **pass** |

## Most often missed or wrong

| Setup | Item | Reports |
| --- | --- | --- |
| multi_agent | Says earnings fall after expiry | 2 |
| multi_agent_rules | Says how many days are left (when 14 or fewer) | 1 |
| multi_agent_rules | Presents the lower-risk alternative the search selected (or says none qualified) | 1 |
| multi_agent_rules | Lists earnings after expiry as a risk to this option | 1 |

## Per report

| Contract | Setup | Facts met | Missing | Mistakes |
| --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | retrieval_verified_tot | 11 of 11 | — | — |
| AAPL 342.5 call 2026-11-20 | multi_agent | 11 of 11 | — | — |
| AAPL 342.5 put 2026-11-20 | retrieval_verified_tot | 11 of 11 | — | — |
| AAPL 342.5 put 2026-11-20 | multi_agent_rules | 11 of 11 | — | — |
| AAPL 342.5 put 2026-11-20 | multi_agent | 10 of 11 | earnings_after | — |
| MSFT 555 call 2026-12-11 | retrieval_verified_tot | 11 of 11 | — | — |
| MSFT 555 call 2026-12-11 | multi_agent_rules | 11 of 11 | — | — |
| MSFT 555 call 2026-12-11 | multi_agent | 10 of 11 | earnings_after | — |
| NVDA 185 call 2026-11-20 | retrieval_verified_tot | 10 of 10 | — | — |
| NVDA 185 call 2026-11-20 | multi_agent | 10 of 10 | — | — |
| TSLA 340 put 2026-11-20 | retrieval_verified_tot | 10 of 10 | — | — |
| TSLA 340 put 2026-11-20 | multi_agent_rules | 9 of 10 | days_left | — |
| KO 96 call 2026-12-11 | retrieval_verified_tot | 9 of 9 | — | — |
| AMD 495 call 2026-12-11 | retrieval_verified_tot | 9 of 9 | — | — |
| AMD 495 call 2026-12-11 | multi_agent_rules | 9 of 9 | — | — |
| SPY 735 call 2026-11-13 | retrieval_verified_tot | 9 of 9 | — | — |
| SPY 735 call 2026-11-13 | multi_agent_rules | 8 of 9 | alternative | — |
| SPY 735 call 2026-11-13 | multi_agent | 9 of 9 | — | — |
| F 14 call 2027-01-15 | retrieval_verified_tot | 9 of 9 | — | — |
| F 14 call 2027-01-15 | multi_agent_rules | 9 of 9 | — | — |
| JPM 320 put 2026-12-11 | retrieval_verified_tot | 10 of 10 | — | — |
| JPM 320 put 2026-12-11 | multi_agent_rules | 10 of 10 | — | — |
| JPM 320 put 2026-12-11 | multi_agent | 10 of 10 | — | — |
| AAPL 342.5 call 2026-11-20 | multi_agent_rules | 11 of 11 | — | earnings_as_risk |
| NVDA 185 call 2026-11-20 | multi_agent_rules | 10 of 10 | — | — |
| TSLA 340 put 2026-11-20 | multi_agent | 10 of 10 | — | — |
| KO 96 call 2026-12-11 | multi_agent_rules | 9 of 9 | — | — |
| KO 96 call 2026-12-11 | multi_agent | 9 of 9 | — | — |
| AMD 495 call 2026-12-11 | multi_agent | 9 of 9 | — | — |
| F 14 call 2027-01-15 | multi_agent | 9 of 9 | — | — |
