import json
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

from instance_lock import is_locked
from position_targets import get_target
from stock_scanner import analyze_stock, stocks as WATCHLIST
import config

load_dotenv()

st.set_page_config(
    page_title="Cortex Trading AI",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background-color: #05070d; color: white; }
h1 { text-align: center; }
.card {
    background: #111827;
    padding: 16px 20px;
    border-radius: 12px;
    border: 1px solid #374151;
    margin-bottom: 10px;
}
.card-green { border-left: 4px solid #22c55e; }
.card-red { border-left: 4px solid #ef4444; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_alpaca_client():
    return TradingClient(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        paper=True
    )


@st.cache_data(ttl=300)
def get_scanner_results():
    results = []
    for symbol in WATCHLIST:
        try:
            results.append(analyze_stock(symbol))
        except Exception:
            pass
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)


st.title("🧠 CORTEX TRADING AI")
st.caption("Autonomous Market Intelligence & Trading System")

col_refresh, col_time = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
with col_time:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.divider()


# ---------- SYSTEM STATUS ----------

alpaca = get_alpaca_client()

cortex_alive = is_locked("autonomous_controller")
discord_alive = is_locked("cortex_discord")

try:
    clock = alpaca.get_clock()
    market_open = clock.is_open
except Exception:
    market_open = None

a, b, c, d = st.columns(4)

with a:
    st.metric("CORTEX ENGINE", "ONLINE" if cortex_alive else "OFFLINE")
with b:
    st.metric("DISCORD BOT", "ONLINE" if discord_alive else "OFFLINE")
with c:
    if market_open is None:
        st.metric("MARKET", "UNKNOWN")
    else:
        st.metric("MARKET", "OPEN" if market_open else "CLOSED")
with d:
    st.metric("TIME", datetime.now().strftime("%H:%M:%S"))

st.divider()


# ---------- ACCOUNT ----------

st.header("💼 Account")

try:
    account = alpaca.get_account()
    equity = float(account.equity)
    last_equity = float(account.last_equity)
    day_pl = equity - last_equity
    day_pl_pct = (day_pl / last_equity * 100) if last_equity else 0

    a, b, c, d = st.columns(4)
    a.metric("Equity", f"${equity:,.2f}")
    b.metric("Cash", f"${float(account.cash):,.2f}")
    c.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    d.metric("Day P/L", f"${day_pl:,.2f}", f"{day_pl_pct:+.2f}%")

except Exception as e:
    st.error(f"Unable to load account: {e}")

st.divider()


# ---------- POSITIONS ----------

st.header("📊 Open Positions")

try:
    positions = alpaca.get_all_positions()

    if not positions:
        st.info("No open positions.")
    else:
        for p in positions:
            entry = float(p.avg_entry_price)
            current = float(p.current_price)
            pl_pct = (current - entry) / entry * 100
            target = get_target(p.symbol)

            card_class = "card card-green" if pl_pct >= 0 else "card card-red"

            target_line = ""
            if target:
                target_line = f"Stop: ${target['stop']:.2f} &nbsp;&nbsp; Target: ${target['target']:.2f}<br>"

            st.markdown(f"""
            <div class="{card_class}">
            <h4>{p.symbol}</h4>
            Qty: {p.qty} &nbsp;&nbsp; Entry: ${entry:.2f} &nbsp;&nbsp; Current: ${current:.2f}<br>
            Unrealized P/L: ${float(p.unrealized_pl):,.2f} ({pl_pct:+.2f}%)<br>
            {target_line}
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Unable to load positions: {e}")

st.divider()


# ---------- PERFORMANCE / TRADE HISTORY ----------

st.header("📈 Performance")

memory = load_json("cortex_memory.json")
completed = [t for t in memory if "profit_loss" in t]

if completed:
    wins = sum(1 for t in completed if t.get("profit_loss", 0) > 0)
    total = len(completed)
    win_rate = wins / total * 100
    total_pl = sum(t.get("profit_loss", 0) for t in completed)

    a, b, c = st.columns(3)
    a.metric("Completed Trades", total)
    b.metric("Win Rate", f"{win_rate:.1f}%")
    c.metric("Total P/L", f"${total_pl:,.2f}")

    st.subheader("Recent Trades")
    for t in reversed(completed[-10:]):
        pl = t.get("profit_loss", 0)
        color = "card-green" if pl >= 0 else "card-red"
        st.markdown(f"""
        <div class="card {color}">
        <b>{t.get('symbol', '?')}</b> &nbsp; {t.get('date', '')}<br>
        Buy: ${t.get('buy_price', 0):.2f} &nbsp; Sell: ${t.get('sell_price', 0):.2f} &nbsp; P/L: ${pl:,.2f}<br>
        <i>{t.get('reason', '')}</i>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No completed trades recorded yet.")

st.divider()


# ---------- SCANNER ----------

st.header("🔍 Market Scanner (top 5, refreshes every 5 min)")

try:
    top = get_scanner_results()[:5]

    cols = st.columns(len(top)) if top else []
    for col, s in zip(cols, top):
        with col:
            st.markdown(f"""
            <div class="card">
            <h4>{s['symbol']}</h4>
            Score: {s['score']}/100<br>
            Bias: {s['bias']}<br>
            Price: ${s['price']}<br>
            RSI: {s['rsi']}
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Scanner unavailable: {e}")

st.caption("Cortex AI — Local Intelligence System")
