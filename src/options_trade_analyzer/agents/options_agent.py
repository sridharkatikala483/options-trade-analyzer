"""Options Analysis agent: a ReAct (Thought -> Action -> Observation -> Finish) agent built with
LangGraph's prebuilt loop. `use_retrieval` switches the RAG tools on or off for comparison."""

import json
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from options_trade_analyzer import config
from options_trade_analyzer.agents.tools import CORE_TOOLS, RETRIEVAL_TOOLS
from options_trade_analyzer.agents.verifier import Verification, revision_request, verify

MAX_STEPS = 14  # tool rounds per invocation; each round is two graph steps (model + tools)
MAX_REVISIONS = 2  # verification-driven revision rounds, as in the design's Critic loop

BASE_PROMPT = """You are the Options Analysis agent in an educational options trade analyzer.
Analyze ONE proposed long option for a retail investor learning options. Never recommend placing a trade.

Work step by step with your tools. You MUST call every tool listed below before writing the
report; a report written without them is rejected automatically.
1. get_option_contract for the requested contract.
2. compute_greeks using the contract's stock price and implied volatility.
3. get_earnings_date. IF the returned date is on or before the expiration, earnings fall before
   expiration; use exactly this date and no other.
4. IF earnings fall before expiration, call compute_greeks again with iv_change_pct=-40 to estimate
   the option's value after a typical post-earnings volatility drop, and compare the two model prices.
5. compare_strategies for the same contract. Use ONLY its numbers for the lower-risk alternative.
{retrieval_steps}
Rules:
- Report every item in get_option_contract's data_quality block: quote age or market-closed status,
  the liquidity rating, the model-vs-market gap, and each model_assumption_flag. Use the liquidity
  rating as given; do not judge liquidity yourself.
- Label model prices after a volatility change as scenarios, not forecasts.
- When presenting the alternative, state its cost, maximum loss, maximum gain and breakeven from the
  tool, and say that lower risk does not guarantee a profit.
- Every number you state must be copied from a tool result; never calculate or invent numbers,
  including hypothetical examples.
- State the stock price, spread, volume and open interest exactly as get_option_contract returned them.
- If a tool returns an error, fix the input and try again.
- Do not recommend buying, selling or any position size; describe risks only.

Finish with a short report in plain language with exactly these headings:
Summary, Key numbers, Data quality, Main risks, Lower-risk alternative, What to watch,
Limits of this analysis.{citation_rule}"""

RETRIEVAL_STEPS = """6. search_options_knowledge for each important risk you found (for example volatility crush,
   time decay, liquidity) and base your explanations on the passages.
7. Always call search_recent_news once for developments that could move the stock before expiration.
"""

CITATION_RULE = """
Cite knowledge passages as [KB: source] and headlines as [News: source, date]. If a search finds
nothing relevant, say so instead of guessing. Retrieved passages give general guidance: compare them
with this contract's actual numbers before applying them; for liquidity, the data_quality rating
decides whether the liquidity passage applies."""


@dataclass
class AnalysisResult:
    report: str
    trace: list[dict] = field(default_factory=list)  # ordered Thought / Action / Observation steps
    verification: Verification | None = None          # checks on the final report
    first_draft_verification: Verification | None = None  # checks before any revision
    revisions: int = 0
    tokens: dict = field(default_factory=lambda: {"input": 0, "output": 0})


def build_agent(use_retrieval: bool = True):
    prompt = BASE_PROMPT.format(
        retrieval_steps=RETRIEVAL_STEPS if use_retrieval else "",
        citation_rule=CITATION_RULE if use_retrieval else "",
    )
    tools = CORE_TOOLS + (RETRIEVAL_TOOLS if use_retrieval else [])
    return create_react_agent(config.get_llm(), tools, prompt=prompt)


def to_trace(messages) -> list[dict]:
    """Convert LangGraph messages into the course's Thought / Action / Observation / Finish steps.

    Observation steps also carry the tool name and arguments so the verifier can read them."""
    trace, pending = [], {}
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            if message.content:
                trace.append({"step": "Thought", "text": str(message.content).strip()})
            for call in message.tool_calls:
                pending[call["id"]] = call
                trace.append({"step": "Action", "text": f"{call['name']}({json.dumps(call['args'])})"})
        elif isinstance(message, ToolMessage):
            call = pending.get(message.tool_call_id, {})
            trace.append({"step": "Observation", "text": str(message.content),
                          "tool": call.get("name", message.name), "args": call.get("args", {})})
        elif isinstance(message, AIMessage):
            trace.append({"step": "Finish", "text": str(message.content).strip()})
        elif isinstance(message, HumanMessage) and trace:
            trace.append({"step": "Critic", "text": str(message.content)})
    return trace


def _token_usage(messages) -> dict:
    usage = {"input": 0, "output": 0}
    for m in messages:
        meta = getattr(m, "usage_metadata", None) or {}
        usage["input"] += meta.get("input_tokens", 0)
        usage["output"] += meta.get("output_tokens", 0)
    return usage


def analyze_contract(ticker: str, option_type: str, strike: float, expiration: str,
                     use_retrieval: bool = True, verify_report: bool = True,
                     max_revisions: int = MAX_REVISIONS) -> AnalysisResult:
    """Run the agent; if verify_report, check the report against the tool outputs and send failures
    back to the agent for revision (at most max_revisions rounds)."""
    request = {"ticker": ticker, "option_type": option_type, "strike": strike, "expiration": expiration}
    agent = build_agent(use_retrieval)
    run_config = {"recursion_limit": 2 * MAX_STEPS + 1}
    messages = [("user", f"Analyze buying the {ticker} {strike:g} {option_type} expiring {expiration}.")]

    state = agent.invoke({"messages": messages}, config=run_config)
    first, revisions = None, 0
    while True:
        trace = to_trace(state["messages"])
        report = trace[-1]["text"] if trace and trace[-1]["step"] == "Finish" and trace[-1]["text"] else ""
        check = verify(report or "(no report)", trace, request, use_retrieval)
        if not report:
            check.issues.insert(0, "The agent finished without writing a report.")
        first = first or check
        if not verify_report or check.passed or revisions >= max_revisions:
            break
        revisions += 1
        state = agent.invoke({"messages": state["messages"] + [HumanMessage(revision_request(check))]},
                             config=run_config)

    return AnalysisResult(
        report=report or "The agent did not finish.",
        trace=trace,
        verification=check,
        first_draft_verification=first,
        revisions=revisions,
        tokens=_token_usage(state["messages"]),
    )
