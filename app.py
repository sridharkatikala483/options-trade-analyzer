"""Streamlit dashboard. Run with:  uv run streamlit run app.py"""

import datetime as dt

import plotly.graph_objects as go
import streamlit as st

from options_trade_analyzer import clock, config
from options_trade_analyzer.analytics.options_math import breakeven, payoff_at_expiry
from options_trade_analyzer.data import get_provider

st.set_page_config(page_title="Options Trade Analyzer", layout="wide")
st.title("AI Options Trade Analyzer")
st.caption("For education only. This tool does not place trades or give financial advice.")

provider = get_provider(config.DATA_PROVIDER)

with st.sidebar:
    ticker = st.text_input("Ticker", "AAPL").upper().strip()
    option_type = st.radio("Option type", ["call", "put"], horizontal=True)
    try:
        expiration = st.selectbox("Expiration", provider.get_expirations(ticker))
    except Exception as exc:
        st.error(f"Could not load expirations: {exc}")
        st.stop()
    chain = provider.get_option_chain(ticker, expiration)[f"{option_type}s"]
    strike = st.selectbox("Strike", chain["strike"].tolist(), index=len(chain) // 2)

spot = provider.get_quote(ticker)
contract = chain[chain["strike"] == strike].iloc[0]
premium = float(contract["lastPrice"])
days_left = (dt.date.fromisoformat(expiration) - clock.today()).days

col1, col2, col3, col4 = st.columns(4)
col1.metric("Stock price", f"${spot:,.2f}")
col2.metric("Premium", f"${premium:,.2f}")
col3.metric("Breakeven", f"${breakeven(option_type, strike, premium):,.2f}")
col4.metric("Days to expiry", days_left)
st.caption(f"Implied volatility: {contract['impliedVolatility']:.1%} · Volume: {contract['volume']} · "
           f"Open interest: {contract['openInterest']}")

prices = [spot * (0.7 + i * 0.006) for i in range(101)]
pnl = [payoff_at_expiry(option_type, strike, premium, p) for p in prices]
fig = go.Figure(go.Scatter(x=prices, y=pnl, mode="lines", name="P&L at expiry"))
fig.add_hline(y=0, line_dash="dot")
fig.add_vline(x=spot, line_dash="dash", annotation_text="Current price")
fig.update_layout(xaxis_title="Stock price at expiry ($)", yaxis_title="Profit / loss per contract ($)")
st.plotly_chart(fig, width="stretch")

st.info("Agent analysis will appear here once the LangGraph workflow is built.")
