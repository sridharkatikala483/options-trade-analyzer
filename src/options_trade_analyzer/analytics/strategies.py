"""Multi-leg strategy math at expiration: cost, maximum loss and gain, breakevens, payoff table.

Every strategy is evaluated with the same quotes and the same expiration, so comparisons are fair.
Positive quantity = bought, negative = sold. Dollar figures are per one set of contracts (x100 shares).
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Leg:
    option_type: Literal["call", "put"]
    strike: float
    premium: float  # per share, paid if bought, received if sold
    quantity: int = 1


def net_cost(legs: list[Leg]) -> float:
    """Dollars paid up front (negative = credit received)."""
    return sum(leg.premium * leg.quantity for leg in legs) * 100


def payoff(legs: list[Leg], price: float) -> float:
    """Profit or loss in dollars if the stock is at `price` on expiration day."""
    value = 0.0
    for leg in legs:
        intrinsic = max(price - leg.strike, 0.0) if leg.option_type == "call" else max(leg.strike - price, 0.0)
        value += intrinsic * leg.quantity
    return value * 100 - net_cost(legs)


def _key_prices(legs: list[Leg]) -> list[float]:
    """Payoff is linear between strikes, so extremes and breakevens sit at strikes or the ends."""
    strikes = sorted({leg.strike for leg in legs})
    return [0.0] + strikes + [strikes[-1] * 3]


def max_loss(legs: list[Leg]) -> float:
    return round(-min(payoff(legs, p) for p in _key_prices(legs)), 2)


def max_gain(legs: list[Leg]) -> float | None:
    """None means unlimited (payoff still rising past the highest strike)."""
    top = max(leg.strike for leg in legs)
    if payoff(legs, top * 3) > payoff(legs, top * 2) + 1e-6:
        return None
    return round(max(payoff(legs, p) for p in _key_prices(legs)), 2)


def breakevens(legs: list[Leg]) -> list[float]:
    """Stock prices at expiration where the position neither makes nor loses money."""
    prices = _key_prices(legs)
    points = []
    for low, high in zip(prices, prices[1:]):
        a, b = payoff(legs, low), payoff(legs, high)
        if a == 0:
            points.append(low)
        if a * b < 0:
            points.append(low + (high - low) * a / (a - b))
    return sorted({round(p, 2) for p in points})


def summarize(name: str, legs: list[Leg], prices: list[float]) -> dict:
    gain = max_gain(legs)
    return {
        "strategy": name,
        "legs": [f"{'buy' if l.quantity > 0 else 'sell'} {abs(l.quantity)} {l.strike:g} {l.option_type} @ {l.premium:.2f}"
                 for l in legs],
        "cost": round(net_cost(legs), 2),
        "max_loss": max_loss(legs),
        "max_gain": "unlimited" if gain is None else gain,
        "breakevens": breakevens(legs),
        "payoff_at_expiry": {f"{p:.2f}": round(payoff(legs, p), 2) for p in prices},
    }
