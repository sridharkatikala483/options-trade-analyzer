# Limits of the Black-Scholes model

## Assumptions
Black-Scholes assumes European exercise (only at expiration), constant volatility, continuous trading and no dividends unless adjusted for. Real markets break these assumptions, especially around events and in thinly traded contracts.

## American-style options
US equity options are American-style and can be exercised early. Black-Scholes values are therefore approximations, usually close for calls on non-dividend stocks but less accurate for deep in-the-money puts and for calls just before an ex-dividend date. Greeks are estimates, not guarantees.
