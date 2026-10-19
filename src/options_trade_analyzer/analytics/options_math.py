"""Deterministic option calculations. The LLM never does this math itself.

Black-Scholes assumes European exercise, so for US equity options (American style)
these values are an approximation.
"""

from typing import Literal

from vollib.black_scholes import black_scholes
from vollib.black_scholes.greeks.analytical import delta, gamma, rho, theta, vega

OptionType = Literal["call", "put"]


def _flag(option_type: OptionType) -> str:
    return "c" if option_type == "call" else "p"


def bs_price(option_type: OptionType, spot: float, strike: float, years: float, rate: float, iv: float) -> float:
    return black_scholes(_flag(option_type), spot, strike, years, rate, iv)


def greeks(option_type: OptionType, spot: float, strike: float, years: float, rate: float, iv: float) -> dict[str, float]:
    """Theta is per calendar day; vega and rho are per 1 percentage-point change."""
    flag = _flag(option_type)
    return {
        "delta": delta(flag, spot, strike, years, rate, iv),
        "gamma": gamma(flag, spot, strike, years, rate, iv),
        "theta": theta(flag, spot, strike, years, rate, iv),
        "vega": vega(flag, spot, strike, years, rate, iv),
        "rho": rho(flag, spot, strike, years, rate, iv),
    }


def breakeven(option_type: OptionType, strike: float, premium: float) -> float:
    return strike + premium if option_type == "call" else strike - premium


def payoff_at_expiry(option_type: OptionType, strike: float, premium: float, price_at_expiry: float, contracts: int = 1) -> float:
    """Profit or loss for a long option position, in dollars (100 shares per contract)."""
    if option_type == "call":
        intrinsic = max(price_at_expiry - strike, 0.0)
    else:
        intrinsic = max(strike - price_at_expiry, 0.0)
    return (intrinsic - premium) * 100 * contracts
