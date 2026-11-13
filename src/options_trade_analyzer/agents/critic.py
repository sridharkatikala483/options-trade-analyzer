"""LLM Critic: the judgment stage that runs after the rule-based verifier passes.

The rules already guarantee that every number, date and citation traces to a tool and that there is
no advice. What they cannot see is meaning: a correct number used for the wrong thing, earnings after
expiry presented as a risk, an alternative whose different expiration is never mentioned. The Critic
reads the report against the team's findings and evidence with a fixed checklist and names the agent
that owns each problem, so the fix goes back to that agent. Its reply is JSON; anything unreadable
counts as no issues (recorded as an error), so a confused Critic can never block a report.

It uses the default model with qwen3 thinking on: on the trial report, thinking on found a real misused
number in 9.4 minutes, while thinking off answered in 24 seconds with a review that was itself wrong.
On a hosted model (Claude Haiku) the review takes seconds.
"""

import json
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

AGENTS = ("writer", "options_analyst", "market_context", "risk_strategist")
MAX_ISSUES = 5

CRITIC_PROMPT = """You are the Critic in a team that explains one proposed options trade to a beginner.
The report already passed automatic checks: every number appears in a tool output, dates and citations
are valid, and it gives no advice. Your job is judgment: find statements that are wrong or misleading
given the evidence, and say which agent must fix each one.

Check only these, and only flag clear problems you can point to in the evidence:
1. A claim that contradicts the evidence or the findings (for example the liquidity rating, which side
   of the expiration the earnings fall on, or the trend direction).
2. Earnings that fall after the expiration presented as a risk to this option, including any line saying
   they "may impact" or "could affect" the stock or its volatility before expiry. Saying they fall after
   expiry and cannot affect this option is correct; general background about earnings is not a problem.
3. The alternative's expiration left out when it differs from the original contract's expiration.
4. A volatility-drop price or a probability presented as a forecast instead of a scenario or estimate.
5. No statement that lower risk does not guarantee a profit.
6. Two findings that conflict without the report explaining it (for example a rising trend but too
   little time left, or an alternative the evidence rates poorly).
7. A number used for the wrong thing (for example the alternative's maximum loss described as the
   original contract's).
Do not flag style, length, formatting or word choice. Quote numbers only as they appear in the evidence;
never compute new ones (the Writer may only use numbers the tools returned).

Owners: writer (the report's wording), options_analyst (contract, Greeks, liquidity), market_context
(trend, earnings date, news), risk_strategist (maximum loss, volatility-drop scenario, alternative).
Send a problem to a specialist only if its own findings are wrong; if the findings are right and the
report misstates them, the problem belongs to the writer.

Reply with JSON only, no other text:
{"issues": [{"agent": "writer", "check": 2, "problem": "...", "evidence": "..."}]}
Reply {"issues": []} if there are no clear problems."""


@dataclass(frozen=True)
class Judgment:
    agent: str
    problem: str
    evidence: str = ""
    check: int | None = None

    def as_issue(self) -> str:
        """The form the team's router reads: 'Judgment issue for <agent>: ...'."""
        return f"Judgment issue for {self.agent}: {self.problem}" + (f" (evidence: {self.evidence})" if self.evidence else "")


JUDGMENT_ISSUE = re.compile(r"Judgment issue for (\w+):")


def parse(text: str) -> tuple[list[Judgment], str | None]:
    """Judgments from the Critic's reply, or ([], reason) when the reply is not the expected JSON."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return [], "no JSON object in the Critic's reply"
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        return [], f"unreadable JSON from the Critic: {exc.msg}"
    items = data.get("issues") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return [], "the Critic's reply has no issues list"
    judgments = []
    for item in items[:MAX_ISSUES]:
        if not isinstance(item, dict) or not str(item.get("problem", "")).strip():
            continue
        agent = item.get("agent") if item.get("agent") in AGENTS else "writer"
        check = item.get("check") if isinstance(item.get("check"), int) else None
        judgments.append(Judgment(agent, str(item["problem"]).strip(), str(item.get("evidence", "")).strip(), check))
    return judgments, None


def review(llm, context: str, report: str) -> tuple[list[Judgment], str | None, object]:
    """Ask the LLM to review `report` against `context` (the findings and evidence the Writer saw)."""
    reply = llm.invoke([SystemMessage(CRITIC_PROMPT),
                        HumanMessage(f"{context}\n\n## Report to review\n{report}")])
    judgments, error = parse(reply.text)  # text blocks only, not Claude's thinking
    return judgments, error, reply
