# Sample report: WMT 127 call, expiring 2026-11-20

Produced by the agent team (Options Analyst, Market Context, Risk Strategist, Writer, rule Critic and LLM
Critic) on Claude Haiku (`claude-haiku-5-5`), replaying `data/snapshots/2026-11-13-scenarios.json.gz`
(recorded 2026-11-13 during market hours). Outcome: shown, every check passed. About 1 minute, about 1 cent.
Education only: this is not a recommendation to buy or sell.

---

## Summary

This report explains a proposed trade: buying one WMT 127 call expiring 2026-11-20. It is education, not a recommendation to buy or sell. The option costs 4.40 per share ($440 per contract) and has 7 days to expiry. Its maximum loss is the full $440 premium, and it breaks even at 131.40, about 3.08% above the stock price of 127.47. Earnings are due on 2026-11-19, one day before expiration, so the release falls inside the option's life. The analysis also covers a lower-maximum-loss alternative, a bull call spread 127/129 with the same expiration, which has a capped gain and a short leg.

## Key numbers

- **Original contract:** WMT 127 call, expiring 2026-11-20
- **Premium:** 4.40 per share; bid 4.35, ask 4.45; spread 0.10 (2.3% of premium)
- **Implied volatility:** 55.4%
- **Volume / open interest:** 834 / 1,942
- **Maximum loss:** $440 per contract
- **Breakeven:** 131.40, about 3.08% above the stock price
- **Chance of finishing beyond breakeven (model estimate):** about 34.0%
- **Greeks:** delta 0.5385; gamma 0.0392; vega 0.0726; theta -27.5 dollars per contract per day
- **Bid-ask cost to open:** $5.00 per contract
- **Volatility-drop scenario (not a forecast):** if implied volatility falls 40%, from 55.4% to 33.24%, the model price falls to 2.72, and the position would lose about $160.71 from the volatility change alone. Theta is -16.78 dollars per contract per day in that scenario.
- **Alternative: bull call spread 127/129, expiring 2026-11-20** (buy the 127 call at 4.40, sell the 129 call at 3.42)
  - Cost and maximum loss: $97.50
  - Maximum gain: $102.50
  - Breakeven: 127.97, about 0.39% above the stock price
  - Chance beyond breakeven (model estimate): about 46.9%
  - Volatility-drop scenario: loses about $2.79
  - Bid-ask cost to open: $12.50 per contract
  - Score: 80.7 out of 100 (a ranking from the analysis tool, not a forecast)

## Data quality

- **Quote:** status is "fresh," last trade 2026-11-13 13:34 ET, age 0.3 hours.
- **Liquidity:** rated "good," with no issues listed. The alternative's legs are also rated "good."
- **Model versus market:** the model price is 4.32 against a market mid of 4.40, a gap of -1.7%. The gap flag is false, so the model and market roughly agree.
- **Minor discrepancies:** one tool output shows the model price as 4.33, not 4.32, and the stock price appears as 127.47 in the contract and risk data but 127.48 as the last close in the trend data. Neither changes the conclusions.
- **Input risk flag:** the model assumes volatility stays roughly constant, but earnings fall before expiration, so volatility may change. Post-earnings prices are scenarios, not forecasts.
- **Missing data:** none listed for the contract.
- **Failed sources:** none reported.

## Main risks

- **Total loss is possible:** the original can lose its full $440 premium if the stock finishes at or below the strike at expiration.
- **Time decay:** theta is -27.5 dollars per contract per day. Time decay speeds up near expiration, and the buyer must outrun it. [KB: time-decay-theta#2, time-decay-theta#3]
- **Earnings inside the option's life:** earnings are on 2026-11-19, one day before expiration, so the release can move the stock and change implied volatility before the option expires.
- **Volatility drop:** in the scenario where implied volatility falls 40%, the position could lose about $160.71 before any stock move. This is a scenario, not a forecast.
- **All-or-nothing behavior:** at-the-money options close to expiration have the highest gamma, so a small stock move can change the value sharply in either direction. [KB: gamma#2]
- **Headlines:** Investing.com says WMT "may move 5.8%" on the Nov. 19 earnings release [News: Investing.com UK, 2026-11-12]. This is a headline claim, not a forecast from this analysis. Other headlines describe both upside and selling pressure. [News: ad-hoc-news.de, 2026-11-10] [News: Blockchain News, 2026-11-09]
- **Price trend:** the stock is up 8.2% over one month and 11.8% over three months, is above its 50-day average of 114.53, and has a 3-month high of 129.17. Past trends do not guarantee future moves.

## Lower-risk alternative

The selected alternative is a bull call spread 127/129 expiring 2026-11-20, the same expiration as the original. It buys the 127 call at 4.40 and sells the 129 call at 3.42. It costs $97.50 net, which is also its maximum loss, and its maximum gain is $102.50. Its breakeven is 127.97.

Trade-offs compared with the original:

- **Capped gain:** the gain is capped at $102.50 per contract. The original's gain is unlimited.
- **Short leg:** the sold 129 call can be assigned early, and brokers usually require approval and margin for this.
- **Higher cost to open:** the bid-ask cost to open is $12.50 per contract, compared with $5.00 for the original.

A runner-up alternative is the bull call spread 127/129 expiring 2026-11-27, which costs $95.00 with a maximum gain of $105.00 and a breakeven of 127.95. It has the same capped-gain and short-leg trade-offs. It also expires on 2026-11-27, later than the original's 2026-11-20. Its liquidity is rated "fair" rather than "good," and its score is 75.5.

Lower risk does not guarantee a profit.

## What to watch

- **2026-11-19:** the earnings release and the stock's reaction.
- **2026-11-20:** the original and selected alternative expiration.
- **Price relative to 127, 127.97 and 131.40:** the strike, the alternative's breakeven, and the original's breakeven.
- **Implied volatility:** changes around earnings, since a drop in implied volatility can reduce the option's value even if the stock moves.
- **Theta:** the daily decay, which accelerates as expiration approaches.
- **The 3-month high of 129.17:** the level the stock has most recently reached.

## Limits of this analysis

Black-Scholes assumes European-style exercise, so for this American-style option the model price is only an approximation. The chance estimates (34.0% for the original and 46.9% for the alternative) and the volatility-drop figures are model outputs, not forecasts. The scores are rankings from the analysis tool. The analysis uses data as of the quote timestamp and does not account for taxes, commissions beyond the bid-ask spread, or the investor's own circumstances. Headlines are included as reported and were not verified.