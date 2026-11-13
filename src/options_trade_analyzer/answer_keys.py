"""Answer keys: what a correct report about one contract must say, and must not say.

The rule-based verifier checks that a report is *faithful* (every number, date and citation comes from a
tool). An answer key checks that it is *complete and sound*: a report with no unsupported numbers can still
forget that only 7 days are left, or list earnings after expiry as a risk.

Keys are built from the recorded snapshot with the project's own tools, so the facts are exact for that
data and nobody types them by hand. Scoring is plain text and number matching (no LLM): free, fast and
repeatable, but it can miss an unusual wording, so spot-check a few scores by hand.
"""

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass

from options_trade_analyzer.agents import tools
from options_trade_analyzer.agents.verifier import (LOW_LIQUIDITY_WORDS, NUMBER, RECOMMENDATION, _decimals,
                                                    _report_dates, _to_float)

SHORT_DAYS = 14  # with this few days left, a report must say how many
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
NEGATION = re.compile(r"\b(not|no|cannot|can't|won't|doesn't|does not|unaffected|irrelevant|outside)\b", re.I)
RISK_WORDS = re.compile(r"\b(risk|impact|affect|watch|could|may|might|hurt|crush)\w*", re.I)
NO_GUARANTEE = re.compile(r"\b(not|no|never|doesn't|don't|isn't)\b[^.\n]{0,30}\bguarantee", re.I)
GOOD_LIQUIDITY = re.compile(r"\b(good|high|ample|strong|healthy) liquidity\b|\bliquidity is (good|high|fine)\b|"
                            r"\b(highly|very) liquid\b|\beasy to trade\b", re.I)
STALE_WORDS = re.compile(r"\bclosed\b|\bhours? old\b|\bstale\b|\bdelayed\b|\bnot (live|real[- ]time)\b|\blow confidence\b",
                         re.I)


# Contract-free wording for summaries across contracts (an item's own description quotes one contract's values).
GENERIC = {
    "max_loss": "States the maximum loss per contract",
    "breakeven": "States the breakeven",
    "liquidity": "Reports the liquidity rating as given",
    "days_left": f"Says how many days are left (when {SHORT_DAYS} or fewer)",
    "earnings_before": "Says earnings fall before expiry and describes a volatility drop",
    "earnings_after": "Says earnings fall after expiry",
    "liquidity_contradiction": "Calls a contract rated good hard to trade",
    "liquidity_overstated": "Calls a contract rated fair or poor easy to trade",
}


@dataclass(frozen=True)
class Item:
    id: str
    kind: str  # "must" or "must_not"
    description: str


def build_key(provider, contract: dict) -> dict:
    """The facts a correct report depends on, read with the same tools the agents use."""
    data = json.loads(tools.get_option_contract.invoke(contract))
    if "error" in data:
        raise ValueError(f"cannot build a key for {contract}: {data['error']}")
    quality = data["data_quality"]
    earnings = provider.get_next_earnings_date(contract["ticker"])
    facts = {
        "max_loss": data["max_loss_per_contract"],
        "breakeven": data["breakeven"],
        "days_to_expiry": data["days_to_expiry"],
        "liquidity": quality["liquidity"]["rating"],
        "earnings_date": earnings.isoformat() if earnings else None,
        "earnings_before_expiry": None if earnings is None else earnings <= dt.date.fromisoformat(contract["expiration"]),
        "market_closed": quality["quote"].get("status") == "market closed",
        "ex_dividend_flag": any("ex-dividend" in f for f in quality["model_assumption_flags"]),
    }
    return {"contract": contract, "facts": facts, "items": [asdict(i) for i in items_for(facts)]}


def items_for(facts: dict) -> list[Item]:
    f = facts
    items = [
        Item("max_loss", "must", f"States the maximum loss: {f['max_loss']:g} per contract"),
        Item("breakeven", "must", f"States the breakeven: {f['breakeven']:g}"),
        Item("liquidity", "must", f"Reports the liquidity rating as {f['liquidity']}"),
        Item("time_decay", "must", "Explains time decay (theta)"),
        Item("model_limits", "must", "Says Black-Scholes only approximates American-style options"),
        Item("no_guarantee", "must", "Says lower risk does not guarantee a profit"),
        Item("alternative", "must", "Presents the lower-risk alternative the search selected (or says none qualified)"),
        Item("alternative_expiration", "must", "Gives the alternative's expiration when it differs from the original's"),
    ]
    if f["days_to_expiry"] <= SHORT_DAYS:
        items.append(Item("days_left", "must", f"Says only {f['days_to_expiry']} days are left"))
    if f["earnings_before_expiry"]:
        items.append(Item("earnings_before", "must",
                          f"Says earnings ({f['earnings_date']}) fall before expiry and describes a volatility drop"))
    elif f["earnings_before_expiry"] is False:
        items.append(Item("earnings_after", "must", f"Says earnings ({f['earnings_date']}) fall after expiry"))
        items.append(Item("earnings_as_risk", "must_not", "Lists earnings after expiry as a risk to this option"))
    if f["market_closed"]:
        items.append(Item("stale_quote", "must", "Says the quote is from a closed market (not live)"))
    if f["ex_dividend_flag"]:
        items.append(Item("dividend", "must", "Mentions the ex-dividend date before expiry (the model ignores it)"))
    if f["liquidity"] == "good":
        items.append(Item("liquidity_contradiction", "must_not", "Calls a contract rated 'good' hard to trade"))
    else:
        items.append(Item("liquidity_overstated", "must_not", f"Calls a contract rated '{f['liquidity']}' easy to trade"))
    items.append(Item("recommendation", "must_not", "Recommends buying, selling or a position size"))
    return items


# --- scoring ---

def _has_number(text: str, value: float) -> bool:
    for token in NUMBER.findall(text):
        number, decimals = _to_float(token), _decimals(token)
        if number is None or (decimals == 0 and not float(value).is_integer() and abs(value) < 100):
            continue  # "14" must not count as a 14.19 breakeven; "$753" may stand for a 752.5 maximum loss
        if abs(abs(number) - abs(value)) <= 0.5 * 10 ** -decimals + 1e-9:
            return True
    return False


def _has_date(text: str, iso: str) -> bool:
    return dt.date.fromisoformat(iso) in _report_dates(text, int(iso[:4]))


def _sentences(text: str, word: str) -> list[str]:
    return [s for s in SENTENCE.split(text) if word in s.lower()]


def _selected(trace: list[dict]) -> dict | None:
    """What this run's alternative search returned: the selected position, or {} if none qualified."""
    for step in reversed(trace):
        if step.get("tool") == "search_alternatives" and step["step"] == "Observation":
            data = json.loads(step["text"])
            return data.get("selected") or {}
    return None


def check(item_id: str, report: str, facts: dict, contract: dict, trace: list[dict]) -> bool | None:
    """True if the report satisfies the item (for must_not items: True if it avoided the mistake);
    None if the item does not apply to this run."""
    low = report.lower()
    f = facts
    if item_id == "max_loss":
        return _has_number(report, f["max_loss"])
    if item_id == "breakeven":
        return _has_number(report, f["breakeven"])
    if item_id == "liquidity":
        return any(f["liquidity"] in s.lower() for s in _sentences(report, "liquid"))
    if item_id == "time_decay":
        return "time decay" in low or "theta" in low
    if item_id == "model_limits":
        return "black-scholes" in low and any(w in low for w in ("american", "early exercise", "approximat"))
    if item_id == "no_guarantee":
        return bool(NO_GUARANTEE.search(report))
    if item_id in ("alternative", "alternative_expiration"):
        selected = _selected(trace)
        if selected is None:
            return None  # this run did not use the alternative search
        if item_id == "alternative":
            if not selected:
                return bool(re.search(r"\bno (qualifying |suitable |lower-risk )?alternative", low))
            family = selected["strategy"].rsplit(" ", 1)[0]
            return family in low
        if not selected or selected["expiration"] == contract["expiration"]:
            return None
        return _has_date(report, selected["expiration"])
    if item_id == "days_left":
        return bool(re.search(rf"\b{f['days_to_expiry']}\s+(calendar\s+|trading\s+)?days?\b", report, re.I))
    if item_id == "earnings_before":
        return _has_date(report, f["earnings_date"]) and bool(re.search(r"volatility[^.\n]{0,40}(drop|crush|fall)|"
                                                                        r"(drop|crush|fall)[^.\n]{0,40}volatility", low))
    if item_id == "earnings_after":
        return _has_date(report, f["earnings_date"]) and any("after" in s.lower() for s in _sentences(report, "earnings"))
    if item_id == "earnings_as_risk":
        return not any(RISK_WORDS.search(s) and not NEGATION.search(s) for s in _sentences(report, "earnings"))
    if item_id == "stale_quote":
        return bool(STALE_WORDS.search(report))
    if item_id == "dividend":
        return "dividend" in low
    if item_id == "liquidity_contradiction":
        return not LOW_LIQUIDITY_WORDS.search(report)
    if item_id == "liquidity_overstated":
        return not GOOD_LIQUIDITY.search(report)
    if item_id == "recommendation":
        return not RECOMMENDATION.search(report)
    raise ValueError(f"unknown answer-key item: {item_id}")


def score(report: str, key: dict, trace: list[dict]) -> dict:
    """Must items met, must-not mistakes made, and which ones."""
    results = {i["id"]: check(i["id"], report, key["facts"], key["contract"], trace) for i in key["items"]}
    kinds = {i["id"]: i["kind"] for i in key["items"]}
    must = [k for k, ok in results.items() if kinds[k] == "must" and ok is not None]
    must_not = [k for k, ok in results.items() if kinds[k] == "must_not" and ok is not None]
    return {
        "must_met": sum(results[k] for k in must),
        "must_total": len(must),
        "mistakes": sum(not results[k] for k in must_not),
        "missing": [k for k in must if not results[k]],
        "made": [k for k in must_not if not results[k]],
    }
