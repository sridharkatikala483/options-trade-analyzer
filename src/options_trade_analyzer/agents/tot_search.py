"""Tree-of-Thought search for a lower-risk alternative (Checkpoint 4 design).

One thought = one narrowing decision: strategy family (depth 1), then strikes (depth 2), then
expiration (depth 3). The LLM is the thought generator: it proposes choices from a menu of listed
strikes and expirations, and anything not on the menu is discarded (like the lab's parse_equation).
Python is the evaluator (analytics/alternatives.py). A LangGraph loop is the controller: generate ->
evaluate -> select the best 3 (beam search, each surviving family's best first) -> repeat, with the
full tree kept in the graph state.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from options_trade_analyzer import config
from options_trade_analyzer.analytics import alternatives as alt
from options_trade_analyzer.analytics.alternatives import Evaluation, Market

BEAM_WIDTH, MAX_DEPTH = 3, 3
PROPOSALS = {1: 3, 2: 4, 3: 3}  # most choices the generator may propose per node, by depth
TIME_LIMIT_S = 900              # past this, the search stops and returns the best position so far


class Proposer(Protocol):
    def propose(self, question: str, context: str, options: list[str], defaults: list[int],
                k: int) -> tuple[list[int], str]:
        """Pick up to k option indices; return them with a one-line reason."""


class RuleProposer:
    """Always proposes the default choices. Used in tests and when TOT_PROPOSER=rules."""

    calls = fallbacks = 0

    def propose(self, question, context, options, defaults, k):
        return defaults[:k], "default choices"


PROPOSE_PROMPT = """You are the thought generator in a tree search for a lower-risk alternative to a
long option, for an educational options analyzer. Python scores every candidate afterwards, so do not
calculate anything; just choose which candidates are worth scoring.

Trade: {context}
Question: {question}
Options:
{options}

Choose up to {k} options by number, most promising first. Reply with JSON only, for example
{{"choices": [1, 3], "reason": "one short sentence"}}"""


class LLMProposer:
    """Asks the configured LLM (config.get_llm) to propose; invalid replies fall back to the defaults.
    Thinking is off: a menu pick needs no long reasoning, and an empty reply just falls back."""

    def __init__(self, llm=None):
        self.llm = llm or config.get_llm(reasoning=False)
        self.calls = self.fallbacks = 0

    def propose(self, question, context, options, defaults, k):
        self.calls += 1
        menu = "\n".join(f"{i}. {o}" for i, o in enumerate(options, start=1))
        try:
            reply = self.llm.invoke(PROPOSE_PROMPT.format(context=context, question=question, options=menu, k=k))
            content = reply.text
            data = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
            picks = []
            for n in data.get("choices", []):
                if isinstance(n, int) and 1 <= n <= len(options) and n - 1 not in picks:
                    picks.append(n - 1)
            if picks:
                return picks[:k], str(data.get("reason", ""))[:200]
            reason = "no valid choice in the reply"
        except Exception as error:  # unreachable model, no JSON, wrong types
            reason = f"unusable reply ({type(error).__name__})"
        self.fallbacks += 1
        return defaults[:k], f"fallback to default choices: {reason}"


@dataclass
class Node:
    id: int
    parent: int | None
    depth: int
    family: str | None = None
    strikes: tuple[float, ...] | None = None
    expiration: str | None = None
    proposal_reason: str = ""
    evaluation: Evaluation | None = None
    pruned: str | None = None


class SearchState(TypedDict):
    depth: int
    frontier: list[int]
    nodes: list[Node]
    stop: str | None


@dataclass
class Search:
    """One search over one contract; build_graph() wires its steps into a LangGraph loop."""

    market: Market
    option_type: str
    strike: float
    expiration: str
    proposer: Proposer
    earnings: str | None = None
    deadline: float = field(default_factory=lambda: time.monotonic() + TIME_LIMIT_S)

    def __post_init__(self):
        self.bullish = self.option_type == "call"
        self.baseline = alt.original(self.option_type, self.strike, self.expiration, self.market)
        self.context = (f"{self.market.ticker} {self.strike:g} {self.option_type} expiring {self.expiration}; "
                        f"stock ${self.market.spot:.2f}; earnings {self.earnings or 'date unknown'}")

    # --- generate: the LLM proposes children for every node on the frontier ---
    def generate(self, state: SearchState) -> dict:
        depth, nodes = state["depth"] + 1, list(state["nodes"])
        for parent in [nodes[i] for i in state["frontier"]]:
            if depth == 1:
                options = alt.FAMILIES_FOR[self.option_type]
                labels, defaults = list(options), list(range(len(options)))
                question = "Which strategy families could lower the maximum loss while keeping the same market view?"
            elif depth == 2:
                options = alt.strike_choices(parent.family, self.strike, self.expiration, self.market,
                                             alt.STRIKE_MENU_PCT)
                options.sort()
                labels = [self._strike_label(parent.family, s) for s in options]
                default_choices = alt.strike_choices(parent.family, self.strike, self.expiration, self.market,
                                                     alt.DEFAULT_STRIKES_PCT)
                defaults = [options.index(s) for s in default_choices]
                question = (f"Which strikes for the {parent.family}? Balance a lower maximum loss against a "
                            "breakeven the stock can reach.")
            else:
                options = alt.expiration_choices(self.expiration, self.market)
                labels = [e + (" (the original)" if e == self.expiration else "") for e in options]
                defaults = list(range(len(options)))
                question = (f"Which expirations should be tried for the {self._strike_label(parent.family, parent.strikes)}? "
                            "Later ones cost more but give more time.")
            if not options:
                continue
            picks, reason = self.proposer.propose(question, self.context, labels, defaults, PROPOSALS[depth])
            for i in picks:
                child = Node(len(nodes), parent.id, depth, parent.family, parent.strikes, parent.expiration, reason)
                if depth == 1:
                    child.family = options[i]
                elif depth == 2:
                    child.strikes = options[i]
                else:
                    child.expiration = options[i]
                nodes.append(child)
        return {"depth": depth, "nodes": nodes}

    # --- evaluate: Python scores each new node; partial nodes are valued by their best default completion ---
    def evaluate(self, state: SearchState) -> dict:
        # a partial node is completed over every default expiration, not only the original one: a thin
        # original expiration would otherwise prune every family at depth 1 before later ones are tried
        expirations = alt.expiration_choices(self.expiration, self.market)
        for node in (n for n in state["nodes"] if n.depth == state["depth"]):
            if node.depth == 1:
                strike_sets = alt.strike_choices(node.family, self.strike, self.expiration, self.market,
                                                 alt.DEFAULT_STRIKES_PCT)
                completions = [(s, e) for s in strike_sets for e in expirations]
            elif node.depth == 2:
                completions = [(node.strikes, e) for e in expirations]
            else:
                completions = [(node.strikes, node.expiration)]
            results, reasons = [], []
            for strikes, expiration in completions:
                position = alt.build(node.family, strikes, expiration, self.market)
                if isinstance(position, str):
                    reasons.append(position)
                else:
                    results.append(alt.evaluate(position, self.baseline, self.market, self.bullish))
            survivors = alt.rank([r for r in results if not r.pruned])
            node.evaluation = survivors[0] if survivors else (alt.rank(results)[0] if results else None)
            node.pruned = None if survivors else (
                node.evaluation.pruned if node.evaluation else (reasons[0] if reasons else "no listed strikes"))
        return {"nodes": state["nodes"]}

    # --- select: keep the best BEAM_WIDTH nodes, the best of each surviving family first ---
    def select(self, state: SearchState) -> dict:
        depth = state["depth"]
        alive = [n for n in state["nodes"] if n.depth == depth and not n.pruned]
        by_evaluation = {id(n.evaluation): n for n in alive}
        ranked = [by_evaluation[id(e)] for e in alt.rank([n.evaluation for n in alive])]
        # diversity: from depth 2 a family has several strike choices; keep each family's best first so
        # one family cannot crowd out the others
        firsts = [n for i, n in enumerate(ranked) if n.family not in {m.family for m in ranked[:i]}]
        ranked = firsts + [n for n in ranked if n not in firsts]
        frontier = [n.id for n in ranked[:BEAM_WIDTH]]
        stop = None
        if not frontier:
            stop = "every branch was pruned"
        elif depth >= MAX_DEPTH:
            stop = "searched all levels"
        elif time.monotonic() > self.deadline:
            stop = "time limit reached"
        return {"frontier": frontier, "stop": stop}

    def build_graph(self):
        graph = StateGraph(SearchState)
        graph.add_node("generate", self.generate)
        graph.add_node("evaluate", self.evaluate)
        graph.add_node("select", self.select)
        graph.add_edge(START, "generate")
        graph.add_edge("generate", "evaluate")
        graph.add_edge("evaluate", "select")
        graph.add_conditional_edges("select", lambda s: END if s["stop"] else "generate")
        return graph.compile()

    def run(self) -> dict:
        if isinstance(self.baseline, str):
            return {"error": self.baseline}
        root = Node(0, None, 0)
        state = self.build_graph().invoke({"depth": 0, "frontier": [0], "nodes": [root], "stop": None})
        return self.result(state)

    def result(self, state: SearchState) -> dict:
        nodes = state["nodes"][1:]
        scored = [n for n in nodes if n.evaluation]
        # every scored node holds a complete position; rank the distinct survivors
        survivors, seen = [], set()
        for e in alt.rank([n.evaluation for n in scored if not n.pruned]):
            if e.position not in seen:
                seen.add(e.position)
                survivors.append(e)
        reasons: dict[str, int] = {}
        for n in nodes:
            if n.pruned:
                key = re.sub(r"for the .*", "for a leg", n.pruned)
                reasons[key] = reasons.get(key, 0) + 1
        base = alt.evaluate(self.baseline, self.baseline, self.market, self.bullish)
        original = base.summary(self.market)
        for key in ("score", "points"):
            original.pop(key)
        return {
            "stock_price": round(self.market.spot, 2),
            "original": original,
            "selected": survivors[0].summary(self.market) if survivors else None,
            "runner_up": survivors[1].summary(self.market) if len(survivors) > 1 else None,
            "outcome": "alternative found" if survivors else f"no qualifying alternative: {', '.join(reasons) or 'no candidates'}",
            "search": {
                "method": f"beam search, width {BEAM_WIDTH}, {MAX_DEPTH} levels (family, strikes, expiration)",
                "stop": state["stop"],
                "nodes_scored": len(scored),
                "nodes_pruned": sum(reasons.values()),
                "pruning_reasons": reasons,
                "option_chains_loaded": self.market.chains_loaded,
                "llm_proposals": self.proposer.calls,
                "llm_fallbacks": self.proposer.fallbacks,
            },
            "scoring": "100 points: risk reduction 30 (maximum loss plus the bid-ask cost to open), "
                       "breakeven distance 25, chance beyond breakeven 20, volatility-drop exposure 15, "
                       "liquidity 10; pruned if a leg is illiquid, the maximum loss is not lower, the chance "
                       "beyond breakeven is below 15%, or the score is below 40",
            "note": "Mid-price quotes; payoffs at each position's own expiration. The chance is a "
                    "Black-Scholes estimate, not a forecast. Lower maximum loss does not guarantee a profit, "
                    "and spreads cap the gain.",
        }

    def _strike_label(self, family: str, strikes: tuple[float, ...]) -> str:
        option_type, _, signs = alt.FAMILIES[family]
        return " / ".join(f"{'buy' if s > 0 else 'sell'} {k:g} {option_type}" for k, s in zip(strikes, signs))


def exhaustive(market: Market, option_type: str, strike: float, expiration: str) -> list[Evaluation]:
    """Score every path with the default menus (no beam), to measure how often the beam misses the best."""
    baseline = alt.original(option_type, strike, expiration, market)
    results = []
    for family in alt.FAMILIES_FOR[option_type]:
        for strikes in alt.strike_choices(family, strike, expiration, market, alt.DEFAULT_STRIKES_PCT):
            for exp in alt.expiration_choices(expiration, market):
                position = alt.build(family, strikes, exp, market)
                if not isinstance(position, str):
                    results.append(alt.evaluate(position, baseline, market, option_type == "call"))
    return alt.rank([r for r in results if not r.pruned])


def search(provider, ticker: str, option_type: str, strike: float, expiration: str,
           earnings: str | None = None, proposer: Proposer | None = None) -> dict:
    """Run the ToT search for one contract and return JSON-ready results."""
    market = Market(provider, ticker, config.RISK_FREE_RATE)
    if proposer is None:
        proposer = RuleProposer() if config.TOT_PROPOSER == "rules" else LLMProposer()
    return Search(market, option_type, strike, expiration, proposer, earnings).run()
