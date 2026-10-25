"""Checkpoint 3 evidence: does retrieval change the agent's behavior?

Runs the Options Analysis agent on the same contract with and without the retrieval tools, plus two
retrieval-only checks (MMR vs pure relevance on news; the similarity floor on an off-topic query),
and writes everything to docs/retrieval_demo.md.

Run with:  uv run python scripts/retrieval_demo.py AAPL call 350 2026-11-06
(On the local qwen3:8b model each agent run takes several minutes.)
"""

import sys
import time
from datetime import datetime

from options_trade_analyzer import config
from options_trade_analyzer.agents.options_agent import analyze_contract
from options_trade_analyzer.data.news import fetch_headlines
from options_trade_analyzer.retrieval import knowledge
from options_trade_analyzer.retrieval import news as news_retrieval
from options_trade_analyzer.retrieval.vector_index import VectorIndex

OUTPUT = config.PROJECT_ROOT / "docs" / "retrieval_demo.md"


def news_comparison(ticker: str, query: str) -> list[str]:
    fresh = [h for h in fetch_headlines(ticker) if h.age_days <= news_retrieval.MAX_AGE_DAYS]
    index = VectorIndex(config.get_embeddings(), "search_document: ", "search_query: ")
    index.add([h.title for h in fresh], [{"source": h.source} for h in fresh])
    lines = [f"Query: *{query}* — {len(fresh)} fresh headlines indexed.", ""]
    for label, lam in [("Pure relevance (lambda = 1.0)", 1.0), (f"MMR (lambda = {news_retrieval.LAMBDA})", news_retrieval.LAMBDA)]:
        lines += [f"**{label}**", ""]
        for hit in index.search(query, k=news_retrieval.TOP_K, fetch_k=news_retrieval.FETCH_K, lambda_mult=lam):
            lines.append(f"- {hit.score:.2f} — {hit.text} ({hit.metadata['source']})")
        lines.append("")
    return lines


def threshold_check() -> list[str]:
    lines = [f"Similarity floor: {knowledge.MIN_SCORE}", ""]
    for query in ["what happens to implied volatility after earnings", "what is the weather in Paris"]:
        raw = knowledge.get_index().search(query, k=1, min_score=0.0)
        kept = knowledge.search_knowledge(query)
        verdict = f"kept {len(kept)} passage(s)" if kept else "rejected, agent told nothing relevant was found"
        lines.append(f"- *{query}*: best match {raw[0].metadata['source']} at {raw[0].score:.2f} → {verdict}")
    return lines + [""]


def agent_section(title: str, ticker: str, option_type: str, strike: float, expiration: str, use_retrieval: bool) -> list[str]:
    started = time.time()
    result = analyze_contract(ticker, option_type, strike, expiration, use_retrieval=use_retrieval)
    lines = [f"## {title}", "", f"Run time: {time.time() - started:.0f} s", "", "### Trace", ""]
    for step in result.trace[:-1]:
        text = step["text"] if len(step["text"]) < 600 else step["text"][:600] + " …"
        lines.append(f"- **{step['step']}:** `{text}`" if step["step"] != "Thought" else f"- **Thought:** {text}")
    return lines + ["", "### Final report", "", result.report, ""]


def main(ticker: str, option_type: str, strike: float, expiration: str) -> None:
    lines = [
        "# Retrieval demo",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} · model `{config.OLLAMA_MODEL if config.LLM_PROVIDER == 'ollama' else config.ANTHROPIC_MODEL}`"
        f" · contract {ticker} {strike:g} {option_type} expiring {expiration}",
        "",
        "## News retrieval: pure relevance vs MMR",
        "",
        *news_comparison(ticker, f"{ticker} earnings expectations and events that could move the stock before {expiration}"),
        "## Knowledge retrieval: similarity floor",
        "",
        *threshold_check(),
        *agent_section("Agent WITHOUT retrieval", ticker, option_type, strike, expiration, use_retrieval=False),
        *agent_section("Agent WITH retrieval", ticker, option_type, strike, expiration, use_retrieval=True),
    ]
    OUTPUT.write_text("\n".join(lines))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    args = sys.argv[1:] or ["AAPL", "call", "350", "2026-11-06"]
    main(args[0], args[1], float(args[2]), args[3])
