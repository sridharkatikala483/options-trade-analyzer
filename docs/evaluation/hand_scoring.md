# Hand-scoring judgment errors

The rule verifier and the answer keys check what code can check: every number traces to a tool, required
facts are stated, required warnings are present. A **judgment error** is a statement that passes those checks
but would mislead a beginner. This rubric keeps hand scores consistent between reports and between scorers
(Week 5 feedback).

## Procedure

1. Open the report next to the run's tool outputs: the dashboard's Review queue ("Every tool call") or the
   run's `trace` in `docs/evaluation/results_<name>.json`.
2. Read the report section by section. For each statement, ask: does the evidence support it, and would a
   beginner who believed it understand the trade correctly?
3. Record each error once, with its category, the quoted words and the evidence (the tool output that
   contradicts or fails to support it). Several wrong words in one claim are one error.
4. For each answer-key flag (`quality_<name>.md`, "Mistakes"), decide whether it is real or a false alarm and
   record the decision in `data/answer_keys/hand_checks.json` with a note. The acceptance gate counts
   unchecked flags as errors.

## Categories

| Category | Definition | Example from our runs |
| --- | --- | --- |
| Misused number | A correct tool number attached to the wrong thing | The alternative's maximum loss described as the original contract's |
| Misframed risk | A risk that cannot apply presented as a risk, or a real risk dismissed | "Earnings on 2027-01-27 may impact volatility" for an option that expires in December |
| Unstated trade-off | An alternative called lower risk without how its exposure changes | A bull put spread presented without saying its short put can be assigned early |
| Overconfidence | An estimate, scenario or chance stated as fact or certainty | "Volatility crush: No risk (earnings are after expiration)" |
| Contradiction | Two statements in the report conflict, or one conflicts with the evidence | "Liquidity is rated good" next to "low volume could widen spreads" |
| Unsupported claim | A qualitative claim no tool output supports | "Deeply out of the money" for a strike 5% from the stock price |
| Advice | Any recommendation to buy, sell or size a position | "You should buy the call before earnings" |

## Severity

- **Major**: a beginner who believed it could make a worse decision (a wrong risk, a hidden trade-off, advice).
- **Minor**: wording that is loose or confusing but would not change a decision.

The acceptance gate's judgment-error threshold (at most 1 per 10 reports) counts major and minor errors
alike, so it errs strict. Record severity anyway, so a later change to the threshold can use it.

## Borderline cases

- If a beginner could reasonably act on it wrongly, it is an error.
- General background (what a volatility crush is, quoted from a knowledge passage) is not an error, even if it
  mentions earnings for a contract whose earnings fall after expiry.
- A required disclaimer ("this report does not recommend buying") is never advice.
