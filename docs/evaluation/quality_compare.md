# Report quality against answer keys: compare

Updated 2026-11-13 10:47 · snapshot `data/snapshots/2026-11-06.json.gz` · 30 reports

Each report is checked against its contract's answer key: facts a correct report must state, and mistakes it must not make (built from the snapshot with the project's tools; plain text and number matching, so spot-check unusual wordings).

| Setup | Reports | Must-state facts met | Reports with every fact | Mistakes made | Reports with no mistakes |
| --- | --- | --- | --- | --- | --- |
| multi_agent_rules | 10 | 84 of 99 (85%) | 1 | 3 | 7 |
| multi_agent | 10 | 81 of 99 (82%) | 0 | 2 | 8 |
| retrieval_verified_tot | 10 | 76 of 99 (77%) | 0 | 3 | 7 |

## Most often missed or wrong

| Setup | Item | Reports |
| --- | --- | --- |
| multi_agent_rules | Says Black-Scholes only approximates American-style options | 7 |
| multi_agent_rules | Says the quote is from a closed market (not live) | 3 |
| multi_agent_rules | Lists earnings after expiry as a risk to this option | 2 |
| multi_agent_rules | Says lower risk does not guarantee a profit | 2 |
| multi_agent_rules | Says how many days are left (when 14 or fewer) | 2 |
| multi_agent | Says Black-Scholes only approximates American-style options | 7 |
| multi_agent | Says how many days are left (when 14 or fewer) | 4 |
| multi_agent | Says lower risk does not guarantee a profit | 4 |
| multi_agent | Says the quote is from a closed market (not live) | 3 |
| multi_agent | Lists earnings after expiry as a risk to this option | 2 |
| retrieval_verified_tot | Says lower risk does not guarantee a profit | 8 |
| retrieval_verified_tot | Says Black-Scholes only approximates American-style options | 6 |
| retrieval_verified_tot | States the maximum loss per contract | 3 |
| retrieval_verified_tot | Lists earnings after expiry as a risk to this option | 3 |
| retrieval_verified_tot | Gives the alternative's expiration when it differs from the original's | 2 |

## Per report

| Contract | Setup | Facts met | Missing | Mistakes |
| --- | --- | --- | --- | --- |
| AAPL 342.5 call 2026-11-20 | multi_agent_rules | 10 of 11 | stale_quote | — |
| AAPL 342.5 call 2026-11-20 | multi_agent | 9 of 11 | model_limits, days_left | — |
| AAPL 342.5 put 2026-11-20 | retrieval_verified_tot | 10 of 11 | max_loss | earnings_as_risk |
| AAPL 342.5 put 2026-11-20 | multi_agent_rules | 11 of 11 | — | earnings_as_risk |
| AAPL 342.5 put 2026-11-20 | multi_agent | 10 of 11 | days_left | — |
| MSFT 555 call 2026-12-11 | retrieval_verified_tot | 8 of 11 | model_limits, no_guarantee, alternative_expiration | — |
| MSFT 555 call 2026-12-11 | multi_agent_rules | 8 of 11 | model_limits, no_guarantee, stale_quote | — |
| MSFT 555 call 2026-12-11 | multi_agent | 9 of 11 | model_limits, stale_quote | earnings_as_risk |
| NVDA 185 call 2026-11-20 | retrieval_verified_tot | 9 of 10 | model_limits | — |
| NVDA 185 call 2026-11-20 | multi_agent_rules | 8 of 10 | model_limits, days_left | — |
| NVDA 185 call 2026-11-20 | multi_agent | 8 of 10 | model_limits, no_guarantee | — |
| TSLA 340 put 2026-11-20 | retrieval_verified_tot | 7 of 10 | no_guarantee, days_left, earnings_after | earnings_as_risk |
| TSLA 340 put 2026-11-20 | multi_agent_rules | 8 of 10 | model_limits, stale_quote | earnings_as_risk |
| TSLA 340 put 2026-11-20 | multi_agent | 9 of 10 | days_left | — |
| KO 96 call 2026-12-11 | retrieval_verified_tot | 8 of 9 | no_guarantee | — |
| KO 96 call 2026-12-11 | multi_agent_rules | 7 of 9 | model_limits, no_guarantee | — |
| KO 96 call 2026-12-11 | multi_agent | 7 of 9 | model_limits, no_guarantee | — |
| AMD 495 call 2026-12-11 | retrieval_verified_tot | 5 of 9 | max_loss, model_limits, no_guarantee, earnings_after | — |
| AAPL 342.5 call 2026-11-20 | retrieval_verified_tot | 8 of 11 | max_loss, no_guarantee, days_left | — |
| AMD 495 call 2026-12-11 | multi_agent_rules | 8 of 9 | model_limits | — |
| AMD 495 call 2026-12-11 | multi_agent | 7 of 9 | model_limits, no_guarantee | — |
| SPY 735 call 2026-11-13 | retrieval_verified_tot | 7 of 9 | model_limits, no_guarantee | — |
| SPY 735 call 2026-11-13 | multi_agent_rules | 7 of 9 | max_loss, days_left | — |
| SPY 735 call 2026-11-13 | multi_agent | 7 of 9 | days_left, stale_quote | — |
| F 14 call 2027-01-15 | retrieval_verified_tot | 7 of 9 | model_limits, no_guarantee | — |
| F 14 call 2027-01-15 | multi_agent_rules | 8 of 9 | model_limits | — |
| F 14 call 2027-01-15 | multi_agent | 8 of 9 | model_limits | — |
| JPM 320 put 2026-12-11 | retrieval_verified_tot | 7 of 10 | model_limits, no_guarantee, alternative_expiration | earnings_as_risk |
| JPM 320 put 2026-12-11 | multi_agent_rules | 9 of 10 | model_limits | liquidity_overstated |
| JPM 320 put 2026-12-11 | multi_agent | 7 of 10 | model_limits, no_guarantee, stale_quote | earnings_as_risk |
