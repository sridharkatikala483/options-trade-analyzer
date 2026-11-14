# Report quality against answer keys: haiku_notot_core

Updated 2026-11-13 20:34 · snapshot `data/snapshots/2026-11-06.json.gz` · 10 reports

Each report is checked against its contract's answer key: facts a correct report must state, and mistakes it must not make (built from the snapshot with the project's tools; plain text and number matching, so spot-check unusual wordings).

| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |
| --- | --- | --- | --- | --- | --- |
| retrieval_verified | 10 | 87 of 87 (100%) | 10 | 0 | 10 |

## Acceptance gate

Thresholds from `acceptance.py` (Week 5 feedback). Judgment errors count answer-key mistakes not ruled out by hand in `data/answer_keys/hand_checks.json` (0 ruled out for this file).

| Threshold | Target | retrieval_verified |
| --- | --- | --- |
| Required tools used (final reports) | >= 100% | ✅ 100% |
| Numbers, dates or citations no tool returned (final reports) | <= 0 | ❌ 1 |
| Reports that recommend a trade or size | <= 0 | ✅ 0 |
| Judgment errors per 10 reports (answer-key mistakes not ruled out by hand) | <= 1.0 | ✅ 0.0 |
| Required facts stated (answer keys) | >= 90% | ✅ 100% |
| Runs held for human review | <= 20% | ✅ 10% |
| Average seconds per run (target set for a hosted model) | <= 120 | ✅ 23 |
| **All thresholds** | | **fail** |

## Most often missed or wrong

| Setup | Item | Reports |
| --- | --- | --- |

## Per report

| Contract | Setup | Facts met | Missing | Mistakes |
| --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | retrieval_verified | 10 of 10 | — | — |
| AAPL 342.5 put 2026-11-20 | retrieval_verified | 10 of 10 | — | — |
| MSFT 555 call 2026-12-11 | retrieval_verified | 9 of 9 | — | — |
| NVDA 185 call 2026-11-20 | retrieval_verified | 9 of 9 | — | — |
| TSLA 340 put 2026-11-20 | retrieval_verified | 9 of 9 | — | — |
| KO 96 call 2026-12-11 | retrieval_verified | 8 of 8 | — | — |
| AMD 495 call 2026-12-11 | retrieval_verified | 8 of 8 | — | — |
| SPY 735 call 2026-11-13 | retrieval_verified | 8 of 8 | — | — |
| F 14 call 2027-01-15 | retrieval_verified | 8 of 8 | — | — |
| JPM 320 put 2026-12-11 | retrieval_verified | 8 of 8 | — | — |
