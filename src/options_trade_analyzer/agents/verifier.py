"""Rule-based verification of an agent report against the tool outputs from the same run.

This is the number-consistency check and the first, deterministic part of the Critic: it never asks
an LLM whether the report is right; it compares the report with what the tools actually returned.

Checks:
  completeness    every required tool was called (conditional on earnings and retrieval)
  tool inputs     Greeks and strategy calls used the contract's real price, IV, strike and expiry
  numbers         every number in the report appears in a tool result (allowing for rounding)
  dates           every date in the report is one the tools returned (earnings, expiry, quote, news)
  liquidity       liquidity wording agrees with the code's liquidity rating
  citations       each [KB: id] was retrieved in this run; [News: ...] only if news was searched
  recommendation  no advice to buy, sell or size a position
"""

import datetime as dt
import json
import re
from dataclasses import dataclass, field

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

KB_CITATION = re.compile(r"\[KB:\s*([^\]]+)\]", re.I)
NEWS_CITATION = re.compile(r"\[News:\s*([^\]]+)\]", re.I)
ISO_DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
WORD_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?"
                       r"(?:,?\s+(20\d\d))?\b", re.I)
NUMBER = re.compile(r"(?<![\w.#])[-−]?\$?\d[\d,]*(?:\.\d+)?%?")
DAY_COUNT = re.compile(r"(?<![\w.#])(\d{1,3})\s+(?:calendar\s+|trading\s+)?days?\b", re.I)
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.M)
LOW_LIQUIDITY_WORDS = re.compile(
    r"\bwid(e|er|en|ening)\b[^.\n]{0,40}\bspreads?\b|\bspreads?\b[^.\n]{0,25}\bwide\b|\billiquid|"
    r"\blow (volume|open interest|liquidity)\b|\bpoor liquidity\b|\bthin(ly)? traded\b", re.I)
RECOMMENDATION = re.compile(
    r"\b(I|we) recommend\b|\byou should (buy|sell|enter|open)\b|\brecommend(ed)? (buying|selling)\b|"
    r"\bgood (trade|buy)\b", re.I)
SMALL_INT_LIMIT = 12  # counts such as "2 rounds" or "3 risks" are not checked


@dataclass
class ToolCall:
    name: str
    args: dict
    result: dict


@dataclass
class Verification:
    issues: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.issues


def tool_calls(trace: list[dict]) -> list[ToolCall]:
    calls = []
    for step in trace:
        if step["step"] == "Observation" and "tool" in step:
            try:
                result = json.loads(step["text"])
            except json.JSONDecodeError:
                result = {"raw": step["text"]}
            calls.append(ToolCall(step["tool"], step.get("args", {}), result if isinstance(result, dict) else {}))
    return calls


def _numbers_in(value) -> list[float]:
    """Every number inside a tool result, including numbers embedded in strings and dict keys."""
    found = []
    if isinstance(value, bool):
        return found
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        return [_to_float(m) for m in NUMBER.findall(value) if _to_float(m) is not None]
    if isinstance(value, dict):
        for k, v in value.items():
            found += _numbers_in(k) + _numbers_in(v)
    if isinstance(value, list):
        for v in value:
            found += _numbers_in(v)
    return found


def _to_float(token: str) -> float | None:
    cleaned = token.replace("$", "").replace(",", "").replace("%", "").replace("−", "-")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _decimals(token: str) -> int:
    digits = token.rstrip("%")
    return len(digits.split(".")[1]) if "." in digits else 0


def _matches(value: float, decimals: int, allowed: set[float]) -> bool:
    tolerance = 0.5 * 10 ** -decimals + 1e-9
    return any(abs(abs(value) - abs(a)) <= tolerance for a in allowed)


def _report_dates(text: str, year: int) -> set[dt.date]:
    dates = {dt.date(int(y), int(m), int(d)) for y, m, d in ISO_DATE.findall(text)}
    for month, day, yr in WORD_DATE.findall(text):
        try:
            dates.add(dt.date(int(yr) if yr else year, MONTHS[month[:3].lower()], int(day)))
        except (KeyError, ValueError):
            continue
    return dates


def required_tools(calls: list[ToolCall], expiration: str, use_retrieval: bool) -> set[str]:
    required = {"get_option_contract", "compute_greeks", "get_earnings_date", "compare_strategies"}
    if use_retrieval:
        required |= {"search_options_knowledge", "search_recent_news"}
    return required


def verify(report: str, trace: list[dict], request: dict, use_retrieval: bool) -> Verification:
    """Check `report` against the tool calls in `trace`. `request` holds ticker/option_type/strike/expiration."""
    v = Verification()
    calls = tool_calls(trace)
    called = {c.name for c in calls}
    by_name = {c.name: c for c in calls}

    # --- completeness, including the conditional volatility-drop scenario ---
    required = required_tools(calls, request["expiration"], use_retrieval)
    missing = sorted(required - called)
    earnings = by_name.get("get_earnings_date")
    earnings_date = None
    if earnings and earnings.result.get("next_earnings_date") not in (None, "unknown"):
        earnings_date = dt.date.fromisoformat(str(earnings.result["next_earnings_date"]))
        if earnings_date <= dt.date.fromisoformat(request["expiration"]):
            required.add("compute_greeks (iv_change_pct)")
            if not any(c.name == "compute_greeks" and c.args.get("iv_change_pct") for c in calls):
                missing.append("compute_greeks (iv_change_pct)")
    for name in missing:
        v.issues.append(f"Required tool not called: {name}.")

    # --- numbers ---
    allowed = set()
    for c in calls:
        scenario = [c.args["iv_change_pct"]] if c.args.get("iv_change_pct") else []
        for n in _numbers_in(c.result) + [float(x) for x in scenario]:
            allowed |= {n, n * 100, n / 100}
    allowed |= {float(request["strike"])}
    text = KB_CITATION.sub(" ", NEWS_CITATION.sub(" ", report))
    text = ISO_DATE.sub(" ", WORD_DATE.sub(" ", LIST_MARKER.sub(" ", text)))
    unsupported = []
    day_counts = set(DAY_COUNT.findall(text))
    for token in NUMBER.findall(text):
        if token in day_counts and not _matches(float(token), 0, allowed):
            unsupported.append(f"{token} days")
            continue
        value = _to_float(token)
        if value is None or (float(value).is_integer() and abs(value) <= SMALL_INT_LIMIT and "$" not in token):
            continue
        if not _matches(value, _decimals(token), allowed):
            unsupported.append(token)
    for token in sorted(set(unsupported)):
        v.issues.append(f"Number not found in any tool result: {token}.")

    # --- tool inputs must match the contract (a right formula on wrong inputs is still wrong) ---
    input_errors = []
    quote_call = by_name.get("get_option_contract")
    contract = quote_call.result if quote_call else {}
    for c in calls:
        if c.name == "compute_greeks" and contract.get("stock_price"):
            for arg, key in (("stock_price", "stock_price"), ("implied_volatility_pct", "implied_volatility_pct")):
                if arg in c.args and abs(float(c.args[arg]) - float(contract[key])) > 0.011:
                    input_errors.append(f"compute_greeks was called with {arg}={c.args[arg]} but "
                                        f"get_option_contract returned {contract[key]}; recompute with the correct value.")
        if c.name in ("compute_greeks", "compare_strategies", "get_option_contract"):
            if "strike" in c.args and abs(float(c.args["strike"]) - float(request["strike"])) > 1e-6:
                input_errors.append(f"{c.name} was called with strike {c.args['strike']}, not the requested {request['strike']:g}.")
            if c.args.get("expiration") and c.args["expiration"] != request["expiration"]:
                input_errors.append(f"{c.name} was called with expiration {c.args['expiration']}, not {request['expiration']}.")
    # a corrected later call fixes an earlier wrong one: only flag if no call used the right inputs
    if input_errors and not any(
            c.name == "compute_greeks" and not c.args.get("iv_change_pct")
            and abs(float(c.args.get("stock_price", -1)) - float(contract.get("stock_price", -2))) <= 0.011
            for c in calls):
        v.issues += sorted(set(input_errors))
    else:
        input_errors = [e for e in input_errors if "compute_greeks" not in e]
        v.issues += sorted(set(input_errors))

    # --- dates ---
    quote = by_name.get("get_option_contract")
    allowed_dates = {dt.date.fromisoformat(request["expiration"]), dt.date.today()}
    if earnings_date:
        allowed_dates.add(earnings_date)
    if quote:
        last = quote.result.get("data_quality", {}).get("quote", {}).get("last_trade", "")
        allowed_dates |= _report_dates(last, dt.date.today().year)
    news = by_name.get("search_recent_news")
    for item in (news.result.get("results", []) if news else []):
        allowed_dates |= _report_dates(item.get("date", ""), dt.date.today().year)
        allowed_dates |= _report_dates(item.get("headline", ""), dt.date.today().year)
    wrong_dates = sorted(_report_dates(report, int(request["expiration"][:4])) - allowed_dates)
    for d in wrong_dates:
        v.issues.append(f"Date not returned by any tool: {d.isoformat()}"
                        + (f" (the earnings date from get_earnings_date is {earnings_date})." if earnings_date else "."))

    # --- liquidity wording vs the rule-based rating ---
    rating = quote.result.get("data_quality", {}).get("liquidity", {}).get("rating") if quote else None
    contradictions = LOW_LIQUIDITY_WORDS.findall(report) if rating == "good" else []
    if contradictions:
        v.issues.append("Report describes liquidity as poor (e.g. wide spread, low volume) but the "
                        "data_quality liquidity rating is 'good'. Use the rating as given.")

    # --- citations ---
    retrieved = {r.get("source") for c in calls if c.name == "search_options_knowledge"
                 for r in c.result.get("results", [])}
    kb_cited = [s.strip() for group in KB_CITATION.findall(report) for s in group.split(",")]
    kb_invalid = sorted({s for s in kb_cited if s not in retrieved})
    for s in kb_invalid:
        v.issues.append(f"Citation [KB: {s}] does not match any passage retrieved in this run.")
    news_sources = {r.get("source", "").lower() for r in (news.result.get("results", []) if news else [])}
    news_cited = NEWS_CITATION.findall(report)
    news_invalid = [c for c in news_cited
                    if not news_sources or not any(src and src in c.lower() for src in news_sources)]
    for c in news_invalid:
        v.issues.append(f"Citation [News: {c}] does not match a headline returned by search_recent_news.")

    # --- no advice ---
    if RECOMMENDATION.search(report):
        v.issues.append("Report contains a recommendation; describe risks only.")

    total_citations = len(kb_cited) + len(news_cited)
    v.metrics = {
        "required_tools": len(required),
        "missing_tools": len(missing),
        "tool_completeness": round(1 - len(missing) / len(required), 2) if required else 1.0,
        "unsupported_numbers": len(set(unsupported)),
        "tool_input_errors": len(set(input_errors)),
        "date_errors": len(wrong_dates),
        "liquidity_contradictions": 1 if contradictions else 0,
        "citations": total_citations,
        "invalid_citations": len(kb_invalid) + len(news_invalid),
        "citation_accuracy": round(1 - (len(kb_invalid) + len(news_invalid)) / total_citations, 2)
        if total_citations else None,
        "recommendation": bool(RECOMMENDATION.search(report)),
    }
    return v


def revision_request(v: Verification) -> str:
    """The feedback message sent back to the agent when verification fails."""
    lines = "\n".join(f"- {issue}" for issue in v.issues)
    return ("Your report failed automatic verification against the tool outputs:\n" + lines +
            "\nCall any missing tools, remove or correct every unsupported number, date and citation, "
            "and then write the complete report again with all required headings.")
