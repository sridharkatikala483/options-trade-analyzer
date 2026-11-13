"""Candidate positions for the lower-risk alternative search: building, scoring and pruning them.

Deterministic Python on top of the payoff and data-quality code, like the ToT lab's solve24(): the
search controller (agents/tot_search.py) decides which candidates to try, this module prices and
judges them. Weights and thresholds follow the Checkpoint 4 design. Prices are mid-quotes, except that
risk reduction counts the bid-ask cost of opening each position (Checkpoint 4 feedback); probabilities
are Black-Scholes (risk-neutral) estimates, not forecasts.
"""

import datetime as dt
import math
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from options_trade_analyzer import clock
from options_trade_analyzer.analytics import options_math, strategies
from options_trade_analyzer.analytics.data_quality import liquidity_rating
from options_trade_analyzer.analytics.strategies import Leg

OptionType = Literal["call", "put"]

WEIGHTS = {"risk_reduction": 30, "breakeven_distance": 25, "chance_beyond_breakeven": 20,
           "volatility_drop": 15, "liquidity": 10}
MIN_SCORE = 40           # complete or partial nodes below this are pruned
MIN_CHANCE = 0.15        # a lower chance of finishing beyond breakeven is a lottery ticket, not lower risk
COUNT_BID_ASK = True     # risk reduction includes the bid-ask cost to open (False: Checkpoint 4 scoring)
TIE_POINTS = 2           # scores this close are ties, broken by max loss, liquidity, then fewer legs
IV_DROP_PCT = -40        # the post-earnings volatility-drop scenario
BREAKEVEN_ZERO_PCT = 10  # a breakeven this far (%) beyond the stock price earns no breakeven points
LIQUIDITY_POINTS = {"good": 1.0, "fair": 0.5}
CHANCE_DROP_PCT = 5      # a chance this many points below the original's is a trade-off the report must state

# family: (option type of its legs, side of the original strike its second strike is on, leg signs)
FAMILIES: dict[str, tuple[OptionType, int, tuple[int, ...]]] = {
    "bull call spread": ("call", +1, (1, -1)),
    "bull put spread": ("put", -1, (-1, 1)),
    "cheaper call": ("call", +1, (1,)),
    "bear put spread": ("put", -1, (1, -1)),
    "bear call spread": ("call", +1, (-1, 1)),
    "cheaper put": ("put", -1, (1,)),
}
FAMILIES_FOR = {"call": ["bull call spread", "bull put spread", "cheaper call"],
                "put": ["bear put spread", "bear call spread", "cheaper put"]}
STRIKE_MENU_PCT = (1.5, 2.5, 3.5, 5.0, 6.0, 7.5, 10.0, 12.5)  # second strike, % of the stock price away
DEFAULT_STRIKES_PCT = (2.5, 5.0, 7.5, 10.0)
LATER_EXPIRATIONS, MAX_LATER_DAYS = 2, 60  # expiration menu: the original plus up to 2 later ones


def years_to_expiry(expiration: str, today: dt.date) -> float:
    return max((dt.date.fromisoformat(expiration) - today).days + 0.5, 0.5) / 365


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


@dataclass(frozen=True)
class Quote:
    strike: float
    bid: float
    ask: float
    iv: float
    liquidity: str  # good / fair / poor, from data_quality.liquidity_rating

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


def _quotes(chain: pd.DataFrame) -> dict[float, Quote]:
    """Two-sided quotes by strike; rows without a bid and an ask are left out."""
    quotes = {}
    for row in chain.itertuples():
        bid, ask = float(row.bid), float(row.ask)
        if bid <= 0 or ask <= 0:
            continue
        volume = int(row.volume) if row.volume == row.volume else 0
        open_interest = int(row.openInterest) if row.openInterest == row.openInterest else 0
        spread_pct = (ask - bid) / ((bid + ask) / 2) * 100
        rating = liquidity_rating(spread_pct, volume, open_interest)["rating"]
        quotes[float(row.strike)] = Quote(float(row.strike), bid, ask, float(row.impliedVolatility), rating)
    return quotes


class Market:
    """What one search reads: the stock price, listed expirations and option chains (cached)."""

    def __init__(self, provider, ticker: str, rate: float, today: dt.date | None = None):
        self.provider, self.ticker, self.rate = provider, ticker, rate
        self.today = today or clock.today()
        self.spot = float(provider.get_quote(ticker))
        self.expirations = sorted(provider.get_expirations(ticker))
        self._chains: dict[str, dict[str, dict[float, Quote]]] = {}

    def quotes(self, expiration: str, option_type: OptionType) -> dict[float, Quote]:
        if expiration not in self._chains:
            raw = self.provider.get_option_chain(self.ticker, expiration)
            self._chains[expiration] = {kind: _quotes(raw[f"{kind}s"]) for kind in ("call", "put")}
        return self._chains[expiration][option_type]

    @property
    def chains_loaded(self) -> int:
        return len(self._chains)


@dataclass(frozen=True)
class Position:
    family: str
    expiration: str
    legs: tuple[Leg, ...]
    ivs: tuple[float, ...]
    liquidity: tuple[str, ...]

    @property
    def name(self) -> str:
        return f"{self.family} {'/'.join(f'{leg.strike:g}' for leg in self.legs)}"

    @property
    def worst_liquidity(self) -> str:
        return max(self.liquidity, key=["good", "fair", "poor"].index)


def build(family: str, strikes: tuple[float, ...], expiration: str, market: Market) -> Position | str:
    """Price a candidate at mid-quotes, or return why it cannot be priced."""
    option_type, _, signs = FAMILIES[family]
    quotes = market.quotes(expiration, option_type)
    legs, ivs, liquidity = [], [], []
    for strike, sign in zip(strikes, signs):
        quote = quotes.get(strike)
        if quote is None:
            return f"no two-sided quote for the {strike:g} {option_type} on {expiration}"
        legs.append(Leg(option_type, strike, quote.mid, sign))
        ivs.append(quote.iv)
        liquidity.append(quote.liquidity)
    return Position(family, expiration, tuple(legs), tuple(ivs), tuple(liquidity))


def original(option_type: OptionType, strike: float, expiration: str, market: Market) -> Position | str:
    """The user's own long option, the baseline every candidate must beat on maximum loss."""
    quote = market.quotes(expiration, option_type).get(strike)
    if quote is None:
        return f"no two-sided quote for the {strike:g} {option_type} on {expiration}"
    return Position("original", expiration, (Leg(option_type, strike, quote.mid),), (quote.iv,), (quote.liquidity,))


def strike_choices(family: str, strike: float, expiration: str, market: Market,
                   steps_pct: tuple[float, ...]) -> list[tuple[float, ...]]:
    """Listed strikes nearest to each step beyond the original strike. Spreads keep the original
    strike as their first leg; a cheaper single option moves its only strike."""
    option_type, side, signs = FAMILIES[family]
    listed = market.quotes(expiration, option_type)
    if len(signs) == 2 and strike not in listed:
        return []
    beyond = [s for s in listed if (s - strike) * side > 0]
    choices = []
    for pct in steps_pct:
        if not beyond:
            break
        target = strike + side * pct / 100 * market.spot
        second = min(beyond, key=lambda s: (abs(s - target), s))
        choice = (strike, second) if len(signs) == 2 else (second,)
        if choice not in choices:
            choices.append(choice)
    return choices


def expiration_choices(expiration: str, market: Market) -> list[str]:
    """The original expiration plus up to two later listed ones within 60 days of it."""
    start = dt.date.fromisoformat(expiration)
    later = [e for e in market.expirations
             if start < dt.date.fromisoformat(e) <= start + dt.timedelta(days=MAX_LATER_DAYS)]
    return [expiration] + later[:LATER_EXPIRATIONS]


@dataclass
class Evaluation:
    position: Position
    score: float
    points: dict[str, float]
    pruned: str | None  # reason, or None if the position survives
    max_loss: float
    breakeven: float | None
    breakeven_distance_pct: float | None
    chance_beyond_breakeven: float
    iv_drop_change: float  # dollars the position gains (+) or loses (-) if implied volatility drops 40%
    open_cost: float = 0.0  # dollars lost to the bid-ask spread when opening

    def summary(self, market: Market) -> dict:
        """The numbers the report may use, in the same shape as compare_strategies."""
        levels = sorted({round(market.spot * f, 2) for f in (0.95, 1.0, 1.05)}
                        | set(strategies.breakevens(list(self.position.legs))))
        data = strategies.summarize(self.position.name, list(self.position.legs), levels)
        data.update({
            "expiration": self.position.expiration,
            "breakeven_distance_pct": self.breakeven_distance_pct,
            "chance_beyond_breakeven_pct": round(self.chance_beyond_breakeven * 100, 1),
            "value_change_if_iv_drops_40pct": self.iv_drop_change,
            "liquidity": self.position.worst_liquidity,
            "bid_ask_cost_to_open": self.open_cost,
            "score": self.score,
            "points": self.points,
        })
        if data["cost"] < 0:
            data["credit_received"] = -data["cost"]
        return data


def open_cost(position: Position, market: Market) -> float:
    """Dollars paid to the bid-ask spread to open the position: half the spread on every leg."""
    cost = 0.0
    for leg in position.legs:
        quote = market.quotes(position.expiration, leg.option_type)[leg.strike]
        cost += (quote.ask - quote.bid) / 2 * abs(leg.quantity) * 100
    return round(cost, 2)


def _model_value(position: Position, spot: float, years: float, rate: float, iv_scale: float) -> float:
    return sum(leg.quantity * options_math.bs_price(leg.option_type, spot, leg.strike, years, rate, iv * iv_scale)
               for leg, iv in zip(position.legs, position.ivs)) * 100


def iv_change(position: Position, market: Market, pct: float) -> float:
    """Dollars the position gains (+) or loses (-) if every leg's implied volatility moves by pct %."""
    years = years_to_expiry(position.expiration, market.today)
    now = _model_value(position, market.spot, years, market.rate, 1.0)
    shifted = _model_value(position, market.spot, years, market.rate, 1 + pct / 100)
    return round(float(shifted - now), 2)


def iv_drop_change(position: Position, market: Market) -> float:
    return iv_change(position, market, IV_DROP_PCT)


def evaluate(position: Position, baseline: Position, market: Market, bullish: bool) -> Evaluation:
    """Score a position out of 100 against the user's original contract and decide whether to prune it."""
    legs, spot = list(position.legs), market.spot
    loss, base_loss = strategies.max_loss(legs), strategies.max_loss(list(baseline.legs))
    cost, base_cost = open_cost(position, market), open_cost(baseline, market)
    # risk compared at the prices actually paid: maximum loss at mid plus the bid-ask cost to open
    paid_loss, base_paid_loss = (loss + cost, base_loss + base_cost) if COUNT_BID_ASK else (loss, base_loss)
    breakevens = [b for b in strategies.breakevens(legs) if b > 0]  # a stock cannot finish at or below $0
    breakeven = (min(breakevens) if bullish else max(breakevens)) if breakevens else None

    years = years_to_expiry(position.expiration, market.today)
    sigma = sum(position.ivs) / len(position.ivs)
    if breakeven is None:
        distance, chance = None, 1.0 if strategies.payoff(legs, spot) >= 0 else 0.0
    else:
        distance = round((breakeven - spot) / spot * 100 * (1 if bullish else -1), 2)
        d2 = (math.log(spot / breakeven) + (market.rate - sigma ** 2 / 2) * years) / (sigma * math.sqrt(years))
        chance = _normal_cdf(d2 if bullish else -d2)

    change, base_change = iv_drop_change(position, market), iv_drop_change(baseline, market)
    exposure = 1.0 if base_change >= 0 else max(0.0, min(1.0, 1 - max(-change, 0) / -base_change))
    if distance is None:  # no breakeven: the position is either profitable everywhere or nowhere
        near = chance
    else:
        near = 1.0 if distance <= 0 else max(0.0, 1 - distance / BREAKEVEN_ZERO_PCT)
    fractions = {
        "risk_reduction": max(0.0, min(1.0, (base_paid_loss - paid_loss) / base_paid_loss)) if base_paid_loss else 0.0,
        "breakeven_distance": near,
        "chance_beyond_breakeven": chance,
        "volatility_drop": exposure,
        "liquidity": min(LIQUIDITY_POINTS.get(r, 0.0) for r in position.liquidity),
    }
    points = {k: round(float(WEIGHTS[k] * f), 1) for k, f in fractions.items()}
    score = round(sum(points.values()), 1)

    direction, base_direction = position_delta(position, market), position_delta(baseline, market)
    if "poor" in position.liquidity:
        pruned = "a leg has poor liquidity"
    elif loss <= 0.005:  # e.g. a credit equal to the strike width: an artifact of mid prices, lost to the spread
        pruned = "no loss at mid prices is a quote artifact, not a real position"
    elif paid_loss >= base_paid_loss - 0.005:  # at the prices actually paid, not only at mid (Week 5 feedback)
        pruned = "maximum loss is not lower than the original"
    elif direction * base_direction <= 0:
        pruned = "it does not move with the stock the way the original does"
    elif chance < MIN_CHANCE:
        pruned = f"chance beyond breakeven below {MIN_CHANCE:.0%}"
    elif score < MIN_SCORE:
        pruned = f"score below {MIN_SCORE}"
    else:
        pruned = None
    return Evaluation(position, score, points, pruned, loss, breakeven, distance, float(chance), change, cost)


def position_delta(position: Position, market: Market) -> float:
    """Shares-equivalent exposure to the stock price (positive gains when the stock rises)."""
    years = years_to_expiry(position.expiration, market.today)
    return sum(leg.quantity * options_math.greeks(leg.option_type, market.spot, leg.strike, years, market.rate, iv)["delta"]
               for leg, iv in zip(position.legs, position.ivs)) * 100


def trade_offs(selected: dict, original: dict, bullish: bool) -> list[dict]:
    """How the alternative's exposure differs from the original's, from the two summaries the search returns.

    Lower maximum loss is never the whole story (Week 5 feedback): a spread caps the gain, a short leg can be
    assigned, a credit spread profits from the stock standing still rather than moving, a different
    expiration changes the time at risk, and a cheaper position may be less likely to pay off. Each item is
    one the report must state; the verifier checks it."""
    out = []
    gain, base_gain = selected["max_gain"], original["max_gain"]
    if gain != "unlimited" and (base_gain == "unlimited" or gain < base_gain - 0.005):
        was = "unlimited" if base_gain == "unlimited" else f"${base_gain:,.2f}"
        out.append({"id": "capped_gain", "text": f"Its gain is capped at ${gain:,.2f} per contract; the original's "
                                                f"maximum gain is {was}."})
    shorts = [text.split(" ", 2)[2].split(" @")[0] for text in selected["legs"] if text.startswith("sell")]
    if shorts:
        out.append({"id": "short_leg", "text": f"It sells the {' and '.join(shorts)}: a short option can be assigned "
                                              "early, and brokers usually require approval and margin for it."})
    if selected["cost"] < 0:
        side = "above" if bullish else "below"
        out.append({"id": "credit", "text": f"It collects ${-selected['cost']:,.2f} up front but can lose up to "
                                           f"${selected['max_loss']:,.2f}: it profits if the stock stays {side} its "
                                           "breakeven, not from a large move."})
    if selected["expiration"] != original["expiration"]:
        when = "later" if selected["expiration"] > original["expiration"] else "earlier"
        out.append({"id": "different_expiration", "expiration": selected["expiration"], "text": f"It expires on {selected['expiration']}, {when} than the "
                                                         f"original ({original['expiration']})."})
    chance, base_chance = selected["chance_beyond_breakeven_pct"], original["chance_beyond_breakeven_pct"]
    if chance < base_chance - CHANCE_DROP_PCT:
        out.append({"id": "lower_chance", "text": f"It is less likely to pay off: a {chance}% chance of finishing "
                                                 f"beyond breakeven versus {base_chance}% for the original "
                                                 "(Black-Scholes estimates, not forecasts)."})
    return out


def rank(evaluations: list[Evaluation]) -> list[Evaluation]:
    """Best first. Scores within TIE_POINTS of the leader are ties, broken by lower maximum loss, then
    better liquidity, then fewer legs, so the same market data always gives the same order."""
    remaining = sorted(evaluations, key=lambda e: -e.score)
    ordered = []
    while remaining:
        leader = remaining[0].score
        tied = [e for e in remaining if e.score >= leader - TIE_POINTS]
        pick = min(tied, key=lambda e: (e.max_loss, ["good", "fair", "poor"].index(e.position.worst_liquidity),
                                        len(e.position.legs), -e.score))
        ordered.append(pick)
        remaining.remove(pick)
    return ordered
