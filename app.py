"""Streamlit dashboard: one contract's numbers and payoff, and the multi-agent analysis of it.

Run with:  uv run streamlit run app.py
With DATA_PROVIDER=snapshot in .env, the sidebar offers the recorded contracts (a reliable demo).
The analysis runs in a background thread (jobs.py), so a click, a reload or another browser tab does
not cancel it; the progress box refreshes itself every few seconds. Every run is logged with an outcome
(review.py); runs held for review wait on the "Review queue" page for a person to approve, edit or reject.
"""

import json
import re
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from options_trade_analyzer import clock, config, review
from options_trade_analyzer.jobs import Job, Jobs
from options_trade_analyzer.agents import tools
from options_trade_analyzer.agents.team import SPECIALISTS, analyze_contract_team
from options_trade_analyzer.analytics import strategies
from options_trade_analyzer.analytics.options_math import breakeven
from options_trade_analyzer.analytics.strategies import Leg
from options_trade_analyzer.data import get_provider

REFRESH_SECONDS = 3
AGENT_TITLES = {"options_analyst": "Options Analyst", "market_context": "Market Context",
                "risk_strategist": "Risk Strategist"}
CHECKS = [("Required tools used", "tool_completeness", "{:.0%}"), ("Unsupported numbers", "unsupported_numbers", "{}"),
          ("Date errors", "date_errors", "{}"), ("Liquidity contradictions", "liquidity_contradictions", "{}"),
          ("Invalid citations", "invalid_citations", "{}"), ("Recommendations", "recommendation", "{}"),
          ("Required statements missing or wrong", "statement_issues", "{}"),
          ("Overconfident sentences", "overconfident_sentences", "{}"),
          ("Judgment issues (LLM Critic)", "judgment_issues", "{}")]
OUTCOME_LABELS = {"shown": "Shown", "shown_with_warning": "Shown with a warning",
                  "needs_review": "Held for review", "refused": "Refused"}
LEG = re.compile(r"(buy|sell) (\d+) ([\d.]+) (call|put) @ ([\d.]+)")


def money(text: str) -> str:
    """Streamlit markdown reads $...$ as math; escape dollar signs so prices show as written."""
    return text.replace("$", r"\$")


@st.cache_resource
def jobs() -> Jobs:
    """One job registry per server process: survives page reloads and is shared by browser tabs."""
    return Jobs()


@st.cache_resource
def load_provider():
    provider = get_provider(config.DATA_PROVIDER)
    tools.provider = provider  # the agents read the same source as the page
    return provider


def alternative(result) -> dict | None:
    """The alternative the Risk Strategist's search selected, from its tool output."""
    for step in reversed(result.trace):
        if step.get("tool") == "search_alternatives" and step["step"] == "Observation":
            selected = json.loads(step["text"]).get("selected")
            return selected if selected and selected.get("legs") else None
    return None


def legs(selected: dict) -> list[Leg]:
    out = []
    for text in selected["legs"]:
        if m := LEG.match(text):
            side, qty, strike, kind, price = m.groups()
            out.append(Leg(kind, float(strike), float(price), int(qty) * (1 if side == "buy" else -1)))
    return out


def contract_label(request: dict) -> str:
    return f"{request['ticker']} {request['strike']:g} {request['option_type']} {request['expiration']}"


def review_page() -> None:
    """Runs the checks could not clear wait here for a person; every decision is appended to the log."""
    records, pending = review.runs(), review.queue()
    rate = review.escalation_rate(records)
    c1, c2, c3 = st.columns(3)
    c1.metric("Runs logged", len(records))
    c2.metric("Held for review", f"{rate:.0%}" if rate is not None else "-", help="Checkpoint 6 target: 20% or less")
    c3.metric("Waiting for a decision", len(pending))

    st.subheader("Waiting for review")
    if not pending:
        st.success("Nothing is waiting for review.")
    else:
        labels = [f"{r['priority']['level'].upper()} · {r['started'][:16].replace('T', ' ')} UTC · "
                  f"{contract_label(r['request'])}" for r in pending]
        run = pending[st.selectbox("Run (most dangerous first, then oldest)", range(len(pending)),
                                   format_func=labels.__getitem__)]
        p = run["priority"]
        show = {"critical": st.error, "high": st.warning}.get(p["level"], st.info)
        show(f"**Priority: {p['level']}.** Most serious problem: {money(p['why'])}")
        st.markdown("**Why it was held**\n\n" + "\n".join(f"- {money(reason)}" for reason in run["reasons"]))
        if run.get("issues"):
            with st.expander("Checks that still fail", expanded=True):
                st.markdown("\n".join(f"- {money(issue)}" for issue in run["issues"]))
        if run.get("flags"):
            st.warning("Risk flags on this contract:\n\n" + "\n".join(f"- {money(f['message'])}" for f in run["flags"]))
        draft = run.get("report") or ""
        edited = st.text_area("Report: edit it here before approving if needed", draft, height=420,
                              key=f"edit-{run['run_id']}")
        note = st.text_input("Note for the log (what you checked or changed)", key=f"note-{run['run_id']}")
        b1, b2, b3 = st.columns(3)
        if b1.button("Approve as written", disabled=not draft, key=f"ok-{run['run_id']}"):
            review.log_review(run["run_id"], "approved", note)
            st.rerun()
        if b2.button("Approve my edited version", disabled=edited.strip() == draft.strip(), key=f"ed-{run['run_id']}"):
            review.log_review(run["run_id"], "edited", note, edited)
            st.rerun()
        if b3.button("Reject", key=f"no-{run['run_id']}"):
            review.log_review(run["run_id"], "rejected", note)
            st.rerun()
        with st.expander("Every tool call in this run"):
            for step in run.get("trace", []):
                if step["step"] == "Observation":
                    st.markdown(f"**{AGENT_TITLES.get(step.get('agent'), step.get('agent', '?'))}** · `{step['tool']}`")
                    st.code(step["text"][:2000], language="json")

    st.subheader("All runs")
    if records:
        st.dataframe(pd.DataFrame([{
            "Started (UTC)": r["started"][:16].replace("T", " "), "Contract": contract_label(r["request"]),
            "Outcome": OUTCOME_LABELS.get(r["outcome"], r["outcome"]),
            "Review": r["review"]["decision"] if r["review"] else ("waiting" if r["outcome"] == "needs_review" else ""),
            "Reviewer note": (r["review"] or {}).get("note", ""), "Run id": r["run_id"]} for r in records]),
            hide_index=True, width="stretch")
    else:
        st.caption("No runs logged yet. Runs started from the analysis page are logged here.")


st.set_page_config(page_title="Options Trade Analyzer", layout="wide")
st.title("AI Options Trade Analyzer")
st.caption("For education only. This tool does not place trades or give financial advice.")

page = st.sidebar.radio("Page", ["Analyze a contract", "Review queue"], horizontal=True)
if page == "Review queue":
    review_page()
    st.stop()

provider = load_provider()
recorded = getattr(provider, "contracts", None)

with st.sidebar:
    st.header("Contract")
    try:
        if recorded:
            st.caption(f"Recorded market data from {provider.recorded_at:%Y-%m-%d %H:%M} UTC (snapshot replay)")
            labels = [f"{c['ticker']} {c['strike']:g} {c['option_type']} {c['expiration']}" for c in recorded]
            pick = recorded[st.selectbox("Recorded contract", range(len(recorded)), format_func=labels.__getitem__)]
            ticker, option_type, expiration, strike = (pick["ticker"], pick["option_type"],
                                                       pick["expiration"], pick["strike"])
            chain = provider.get_option_chain(ticker, expiration)[f"{option_type}s"]
        else:
            ticker = st.text_input("Ticker", "AAPL").upper().strip()
            option_type = st.radio("Option type", ["call", "put"], horizontal=True)
            expiration = st.selectbox("Expiration", provider.get_expirations(ticker))
            chain = provider.get_option_chain(ticker, expiration)[f"{option_type}s"]
            strike = st.selectbox("Strike", chain["strike"].tolist(), index=len(chain) // 2)
    except Exception as exc:  # noqa: BLE001 - show data problems instead of a stack trace
        st.error(f"Could not load market data: {exc}")
        st.stop()
    st.header("Analysis")
    use_critic = st.checkbox("LLM Critic (judgment review)", value=True,
                             help="After the rule checks pass, an LLM reviews the report for judgment errors "
                                  "and sends fixes to the agent responsible. Slower on a local model.")
    model = config.OLLAMA_MODEL if config.LLM_PROVIDER == "ollama" else config.ANTHROPIC_MODEL
    st.caption(f"Model: `{model}` · data: `{config.DATA_PROVIDER}`")

spot = provider.get_quote(ticker)
row = chain[chain["strike"] == strike].iloc[0]
bid, ask = float(row["bid"]), float(row["ask"])
premium = (bid + ask) / 2 if bid > 0 and ask > 0 else float(row["lastPrice"])  # mid-quote, as the agents use
days_left = (pd.Timestamp(expiration).date() - clock.today()).days
key = (ticker, option_type, float(strike), expiration)
label = f"{ticker} {strike:g} {option_type} {expiration}"
job = jobs().by_key.get(key)
result = job.result if job and job.done and not job.error else None

col1, col2, col3, col4 = st.columns(4)
col1.metric("Stock price", f"${spot:,.2f}")
col2.metric("Premium (mid)", f"${premium:,.2f}")
col3.metric("Breakeven", f"${breakeven(option_type, strike, premium):,.2f}")
col4.metric("Days to expiry", days_left)
st.caption(money(f"Bid ${bid:,.2f} · ask ${ask:,.2f} · implied volatility {row['impliedVolatility']:.1%} · "
                 f"volume {row['volume']:g} · open interest {row['openInterest']:g}"))

prices = [spot * (0.8 + i * 0.004) for i in range(101)]
original = [Leg(option_type, float(strike), premium)]
fig = go.Figure(go.Scatter(x=prices, y=[strategies.payoff(original, p) for p in prices], mode="lines",
                           name=f"Buy the {strike:g} {option_type} (expires {expiration})"))
selected = alternative(result) if result else None
if selected and legs(selected):
    fig.add_scatter(x=prices, y=[strategies.payoff(legs(selected), p) for p in prices], mode="lines",
                    name=f"Alternative: {selected['strategy']} (expires {selected['expiration']})")
fig.add_hline(y=0, line_dash="dot")
fig.add_vline(x=spot, line_dash="dash", annotation_text="Current price")
fig.update_layout(xaxis_title="Stock price at expiry ($)", yaxis_title="Profit / loss per contract ($)",
                  legend={"orientation": "h", "y": -0.2})
st.plotly_chart(fig, width="stretch")
if selected and selected["expiration"] != expiration:
    st.caption(f"Each line is the payoff at its own expiration: the alternative expires {selected['expiration']}.")

st.subheader("AI analysis")
st.caption("Five agents analyze this contract: two specialists in parallel, a Risk Strategist, a Writer and a "
           "Critic. " + ("On the local model this takes about 15-45 minutes (less with the LLM Critic off); "
                         "it runs in the background, so you can keep using the page." if config.LLM_PROVIDER == "ollama"
                         else "This takes a minute or two."))



def show_steps(job: Job) -> None:
    for seconds, _, text in job.steps:
        st.write(f"{seconds / 60:4.1f} min · {text}")


@st.fragment(run_every=REFRESH_SECONDS)
def progress(job: Job) -> None:
    """Redraws itself every few seconds while the job runs; reruns the whole page once it is done."""
    if job.done:
        st.rerun()
    with st.status(f"The agents are working on {job.label}... {job.seconds / 60:.1f} min so far", expanded=True):
        show_steps(job)
        st.write(f"**Now:** {job.now_working()} ({job.since_last_step():,.0f} s)")
    st.caption("You can reload the page or browse other contracts; the analysis keeps running.")


busy = jobs().running()
if busy and busy.key != key:
    st.info(f"An analysis of {busy.label} is running ({busy.seconds / 60:.1f} min so far). "
            "Pick that contract in the sidebar to watch it.")
if job and not job.done:
    progress(job)
else:
    if job and job.error:
        st.error(f"The last analysis failed: {job.error}")
    if st.button("Run AI analysis again" if result else "Run AI analysis", type="primary", disabled=busy is not None):
        request = {"ticker": ticker, "option_type": option_type, "strike": float(strike), "expiration": expiration}
        jobs().start(key, label, use_critic, lambda on_step: review.run_and_log(
            request, {"team": True, "llm_critic": use_critic}, lambda: analyze_contract_team(
                ticker, option_type, float(strike), expiration, use_llm_critic=use_critic, on_step=on_step)))
        st.rerun()

if result:
    v, first = result.verification, result.first_draft_verification
    decision = next((r["review"] for r in review.runs() if r["run_id"] == result.run_id), None)
    held = result.outcome == "needs_review" and (decision is None or decision["decision"] == "rejected")
    if result.outcome == "refused":
        st.error(result.reasons[0] if result.reasons else "The request could not be analyzed.")
    elif result.outcome == "needs_review" and decision is None:
        st.error("**Held for human review.** " + " ".join(result.reasons)
                 + " A person decides on the Review queue page; the draft below is not approved.")
    elif decision:
        st.info(f"Held for review, then **{decision['decision']}** by a reviewer"
                + (f": {decision['note']}" if decision.get("note") else "."))
    else:
        st.success(f"The report passed every check{' (rules and LLM Critic)' if job.llm_critic else ' (rules)'}"
                   f" after {result.revisions} fix round(s).")

    report_tab, agents_tab, critic_tab, details_tab, steps_tab = st.tabs(
        ["Report", "Agents' findings", "Critic", "Run details", "Timeline"])
    with report_tab:
        if result.flags:  # computed by code from the contract, not by the agents
            st.warning("**Before you read: this contract has risk flags**\n\n"
                       + "\n".join(f"- {money(f['message'])}" for f in result.flags))
        text = decision["report"] if decision and decision["decision"] == "edited" else result.report
        if held:
            with st.expander("Draft report (held for review: not approved)"):
                st.markdown(money(text))
        else:
            st.markdown(money(text))
    with agents_tab:
        calls = defaultdict(list)
        for step in result.trace:
            if step["step"] == "Observation":
                calls[step.get("agent", "?")].append(step["tool"])
        for name in SPECIALISTS:
            with st.expander(AGENT_TITLES[name], expanded=True):
                st.caption("Tools called: " + (", ".join(calls[name]) or "none"))
                st.markdown(money(result.findings.get(name, "(did not run)")))
    with critic_tab:
        st.markdown("The Critic checks the rules first (every number, date and citation must come from a tool; "
                    "no advice), then, only if they pass, an LLM reviews the report for judgment errors.")
        st.dataframe(pd.DataFrame(
            [{"Check": label, "First draft": fmt.format(first.metrics.get(k, 0)),
              "Final report": fmt.format(v.metrics.get(k, 0))} for label, k, fmt in CHECKS]),
            hide_index=True, width="stretch")
        if result.routing:
            st.markdown("**Fixes sent to agents**")
            st.dataframe(pd.DataFrame([{"Round": r["round"], "Sent to": AGENT_TITLES.get(r["agent"], "Writer"),
                                        "Issues": " · ".join(r["issues"])} for r in result.routing]),
                         hide_index=True, width="stretch")
        if v.issues:
            st.markdown("**Still open**")
            for issue in v.issues:
                st.markdown(f"- {money(issue)}")
    with details_tab:
        c1, c2, c3 = st.columns(3)
        c1.metric("Time", f"{job.seconds / 60:.1f} min")
        c2.metric("Fix rounds", result.revisions)
        c3.metric("Tokens (in / out)", f"{result.tokens['input']:,} / {result.tokens['output']:,}")
        st.caption(f"Model `{model}` · data `{config.DATA_PROVIDER}` · LLM Critic {'on' if job.llm_critic else 'off'}")
    with steps_tab:
        show_steps(job)
