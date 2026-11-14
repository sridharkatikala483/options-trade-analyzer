# Report quality against answer keys: haiku_notot_scenarios

Updated 2026-11-13 20:34 · snapshot `data/snapshots/2026-11-13-scenarios.json.gz` · 12 reports

Each report is checked against its contract's answer key: facts a correct report must state, and mistakes it must not make (built from the snapshot with the project's tools; plain text and number matching, so spot-check unusual wordings).

| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |
| --- | --- | --- | --- | --- | --- |
| retrieval_verified | 12 | 90 of 90 (100%) | 12 | 0 | 12 |

## Acceptance gate

Thresholds from `acceptance.py` (Week 5 feedback). Judgment errors count answer-key mistakes not ruled out by hand in `data/answer_keys/hand_checks.json` (0 ruled out for this file).

| Threshold | Target | retrieval_verified |
| --- | --- | --- |
| Required tools used (final reports) | >= 100% | ✅ 100% |
| Numbers, dates or citations no tool returned (final reports) | <= 0 | ❌ 1 |
| Reports that recommend a trade or size | <= 0 | ✅ 0 |
| Judgment errors per 10 reports (answer-key mistakes not ruled out by hand) | <= 1.0 | ✅ 0.0 |
| Required facts stated (answer keys) | >= 90% | ✅ 100% |
| Runs held for human review | <= 20% | ✅ 8% |
| Average seconds per run (target set for a hosted model) | <= 120 | ✅ 22 |
| **All thresholds** | | **fail** |

## Most often missed or wrong

| Setup | Item | Reports |
| --- | --- | --- |

## Per report

| Contract | Setup | Facts met | Missing | Mistakes |
| --- | --- | --- | --- | --- |
| WMT 127 call 2026-11-20 | retrieval_verified | 8 of 8 | — | — |
| HD 337.5 put 2026-11-20 | retrieval_verified | 8 of 8 | — | — |
| PANW 335 call 2026-11-27 | retrieval_verified | 8 of 8 | — | — |
| ZM 99 put 2026-11-27 | retrieval_verified | 8 of 8 | — | — |
| SPY 753 call 2026-11-13 | retrieval_verified | 7 of 7 | — | — |
| QQQ 672 put 2026-11-13 | retrieval_verified | 7 of 7 | — | — |
| TSLA 490 call 2026-11-20 | retrieval_verified | 8 of 8 | — | — |
| AAPL 315 put 2026-11-27 | retrieval_verified | 8 of 8 | — | — |
| MSFT 470 call 2026-12-18 | retrieval_verified | 8 of 8 | — | — |
| KO 90 put 2027-01-15 | retrieval_verified | 7 of 7 | — | — |
| F 11 put 2026-12-18 | retrieval_verified | 6 of 6 | — | — |
| AMD 560 call 2027-03-19 | retrieval_verified | 7 of 7 | — | — |
