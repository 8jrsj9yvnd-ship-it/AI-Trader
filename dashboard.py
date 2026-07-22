import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MARKET_TZ = ZoneInfo("America/New_York")

import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetPortfolioHistoryRequest

from instance_lock import is_locked
from position_targets import get_target
from stock_scanner import analyze_stock, stocks as WATCHLIST
import config

HEARTBEAT_GIST_URL = "https://gist.githubusercontent.com/8jrsj9yvnd-ship-it/4518b5abd44289f1104c63aac5e5d0ee/raw/status.json"
HEARTBEAT_STALE_AFTER_SECONDS = 150


@st.cache_data(ttl=20)
def get_remote_status():
    """The engine and Discord bot run on a local machine, not on Streamlit Cloud,
    so local lock-file checks (instance_lock.is_locked) always report offline here.
    The local bot publishes a heartbeat to a public Gist every ~60s; treat it as
    alive only if BOTH the flag is true AND the heartbeat isn't stale (covers a
    crash that never got to write a final "false")."""

    try:
        resp = requests.get(f"{HEARTBEAT_GIST_URL}?_={int(datetime.now().timestamp())}", timeout=5)
        data = resp.json()
        last = datetime.fromisoformat(data["last_heartbeat"])
        age = (datetime.now(timezone.utc) - last).total_seconds()
        fresh = age < HEARTBEAT_STALE_AFTER_SECONDS
        return bool(data["engine_alive"]) and fresh, bool(data["discord_alive"]) and fresh
    except Exception:
        return False, False

load_dotenv()

# Streamlit Community Cloud provides credentials via st.secrets, not a .env file.
# Mirror them into os.environ so the existing os.getenv(...) calls below work unchanged
# both locally (no secrets.toml -- st.secrets raises, just fall back to .env) and when deployed.
try:
    for _key in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
        if _key in st.secrets and not os.getenv(_key):
            os.environ[_key] = st.secrets[_key]
except Exception:
    pass

st.set_page_config(
    page_title="Cortex Trading AI",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
<style>
:root {
    --surface-1:     #1a1a19;
    --page:          #0d0d0d;
    --text-primary:  #ffffff;
    --text-secondary:#c3c2b7;
    --text-muted:    #898781;
    --border:        rgba(255,255,255,0.10);
    --gridline:      #2c2c2a;
    --accent:        #3987e5;
    --accent-soft:   #6da7ec;
    --good:          #0ca30c;
    --critical:      #d03b3b;
    --warning:       #fab219;
}

.stApp { background-color: var(--page); color: var(--text-primary); }
.block-container { padding-top: 2rem; max-width: 1200px; }

/* recolor native st.metric to match the palette exactly */
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 0.72rem !important;
}
[data-testid="stMetricValue"] { color: var(--text-primary) !important; }
[data-testid="stMetricDeltaIcon-Up"], [data-testid="stMetricValue"] + div svg[color="green"] { }

.cx-title {
    text-align: center;
    font-weight: 700;
    letter-spacing: 3px;
    font-size: 2.3rem;
    margin-bottom: 0;
    background: linear-gradient(90deg, var(--accent), var(--accent-soft));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.cx-caption { text-align: center; color: var(--text-muted); margin-top: 2px; margin-bottom: 1.2rem; }

.cx-divider { border: none; border-top: 1px solid var(--gridline); margin: 1.6rem 0; }

.cx-section-label {
    color: var(--text-secondary);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
    margin-bottom: 0.7rem;
}

/* status pill: bot/market state, never color alone -- dot + word */
.cx-pill {
    display: flex; align-items: center; gap: 8px;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
}
.cx-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.cx-dot-good { background: var(--good); box-shadow: 0 0 6px var(--good); }
.cx-dot-bad  { background: var(--critical); box-shadow: 0 0 6px var(--critical); }
.cx-dot-warn { background: var(--warning); box-shadow: 0 0 6px var(--warning); }
.cx-pill-label { color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; }
.cx-pill-value { color: var(--text-primary); font-weight: 600; font-size: 0.95rem; }

.cx-hero-wrap {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
}
.cx-hero-label { color: var(--text-secondary); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1.5px; }
.cx-hero-value { font-size: 3rem; font-weight: 700; color: var(--text-primary); line-height: 1.15; }
.cx-hero-delta-good { color: var(--good); font-weight: 600; font-size: 1rem; }
.cx-hero-delta-bad  { color: var(--critical); font-weight: 600; font-size: 1rem; }

.cx-card {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.cx-card-good { border-left-color: var(--good); }
.cx-card-bad  { border-left-color: var(--critical); }
.cx-card-title { font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.cx-card-row { color: var(--text-secondary); font-size: 0.88rem; margin-bottom: 2px; }
.cx-card-row b { color: var(--text-primary); }
.cx-delta-good { color: var(--good); font-weight: 600; }
.cx-delta-bad  { color: var(--critical); font-weight: 600; }
.cx-muted { color: var(--text-muted); font-size: 0.82rem; font-style: normal; }

.cx-meter-label { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); margin-top: 8px; }
.cx-meter-track { height: 6px; border-radius: 3px; overflow: hidden; margin-top: 4px; }
.cx-meter-fill { height: 100%; border-radius: 3px; }

.stButton button {
    background: var(--surface-1);
    color: var(--text-primary);
    border: 1px solid var(--border);
}
.stButton button:hover { border-color: var(--accent); color: var(--accent-soft); }

/* native st.info/st.error/st.success alert boxes default to a light theme
   that clashes hard against this dark surface -- recolor them onto the
   same tokens as everything else instead of leaving Streamlit's defaults */
[data-testid="stAlert"] {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
}
[data-testid="stAlertContentInfo"] { color: var(--text-secondary); }
[data-testid="stAlertContentError"] { color: var(--critical); }
[data-testid="stAlertContentInfo"] svg, [data-testid="stAlertContentError"] svg { display: none; }

.cx-badge-good  { color: var(--good); font-weight: 600; }
.cx-badge-warn  { color: var(--warning); font-weight: 600; }
.cx-badge-muted { color: var(--text-muted); font-weight: 600; }
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
def get_ytd_return(current_equity):
    """Percent change from the first equity value on record this calendar year
    to now. Note: for a newly-funded account, that first value is the funding
    date, not Jan 1 -- Alpaca zero-pads days before the account existed, so we
    skip those rather than treat $0 as a real starting balance."""
    req = GetPortfolioHistoryRequest(start=datetime(datetime.now().year, 1, 1), end=datetime.now(), timeframe="1D")
    hist = get_alpaca_client().get_portfolio_history(req)
    for eq in hist.equity:
        if eq:
            start_equity = eq
            return (current_equity - start_equity) / start_equity * 100
    return None


@st.cache_data(ttl=60)
def get_equity_curve():
    req = GetPortfolioHistoryRequest(period="1D", timeframe="15Min")
    hist = get_alpaca_client().get_portfolio_history(req)
    points = [
        (datetime.fromtimestamp(t), eq)
        for t, eq in zip(hist.timestamp, hist.equity)
        if eq is not None
    ]
    return points


def render_equity_chart(points):
    if len(points) < 2:
        st.info("Not enough intraday data yet to plot today's equity curve.")
        return

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    line_color = "#3987e5"

    # Equity moves within a narrow band relative to its absolute level -- autorange
    # to the data (never force a zero baseline, or the day's real movement flattens
    # to an invisible sliver at the top of an otherwise-empty chart).
    pad = max((max(ys) - min(ys)) * 0.15, 1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color=line_color, width=2, shape="spline", smoothing=0.3),
        hovertemplate="$%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#1a1a19", bordercolor="rgba(255,255,255,0.10)", font_color="#ffffff"),
        showlegend=False,
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(color="#898781", size=11),
            tickformat="%H:%M",
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#2c2c2a", gridwidth=1, zeroline=False,
            tickfont=dict(color="#898781", size=11),
            tickprefix="$", tickformat=",.0f",
            range=[min(ys) - pad, max(ys) + pad],
        ),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


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


def status_pill(label, value, state):
    """state: 'good' | 'bad' | 'warn'"""
    dot_class = {"good": "cx-dot-good", "bad": "cx-dot-bad", "warn": "cx-dot-warn"}[state]
    st.markdown(f"""
    <div class="cx-pill">
        <div class="cx-dot {dot_class}"></div>
        <div>
            <div class="cx-pill-label">{label}</div>
            <div class="cx-pill-value">{value}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


st.markdown('<div class="cx-title">🧠 CORTEX TRADING AI</div>', unsafe_allow_html=True)
st.markdown('<div class="cx-caption">Autonomous Market Intelligence &amp; Trading System</div>', unsafe_allow_html=True)

col_refresh, col_time = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
with col_time:
    st.markdown(f'<div style="color:var(--text-muted); padding-top:8px;">Last updated: {datetime.now(MARKET_TZ).strftime("%Y-%m-%d %H:%M:%S")} ET</div>', unsafe_allow_html=True)

st.markdown('<hr class="cx-divider">', unsafe_allow_html=True)


# ---------- SYSTEM STATUS ----------

alpaca = get_alpaca_client()

cortex_alive = is_locked("autonomous_controller")
discord_alive = is_locked("cortex_discord")

if not cortex_alive and not discord_alive:
    # Local lock files aren't visible when running on Streamlit Cloud (the bots
    # run on a different machine) -- fall back to the shared heartbeat instead.
    cortex_alive, discord_alive = get_remote_status()

try:
    clock = alpaca.get_clock()
    market_open = clock.is_open
except Exception:
    market_open = None

a, b, c, d = st.columns(4)

with a:
    status_pill("Cortex Engine", "ONLINE" if cortex_alive else "OFFLINE", "good" if cortex_alive else "bad")
with b:
    status_pill("Discord Bot", "ONLINE" if discord_alive else "OFFLINE", "good" if discord_alive else "bad")
with c:
    if market_open is None:
        status_pill("Market", "UNKNOWN", "warn")
    else:
        status_pill("Market", "OPEN" if market_open else "CLOSED", "good" if market_open else "warn")
with d:
    status_pill("Market Time", datetime.now(MARKET_TZ).strftime("%H:%M:%S") + " ET", "good")

st.markdown('<hr class="cx-divider">', unsafe_allow_html=True)


# ---------- ACCOUNT ----------

st.markdown('<div class="cx-section-label">💼 Account</div>', unsafe_allow_html=True)

try:
    account = alpaca.get_account()
    equity = float(account.equity)
    last_equity = float(account.last_equity)
    day_pl = equity - last_equity
    day_pl_pct = (day_pl / last_equity * 100) if last_equity else 0
    delta_class = "cx-hero-delta-good" if day_pl >= 0 else "cx-hero-delta-bad"
    arrow = "▲" if day_pl >= 0 else "▼"

    ytd_pct = get_ytd_return(equity)
    ytd_line = ""
    if ytd_pct is not None:
        ytd_class = "cx-hero-delta-good" if ytd_pct >= 0 else "cx-hero-delta-bad"
        ytd_arrow = "▲" if ytd_pct >= 0 else "▼"
        ytd_line = f'<div class="{ytd_class}" style="margin-top:2px;">{ytd_arrow} {ytd_pct:+.2f}% YTD</div>'

    hero_col, rest_col = st.columns([1.3, 2])

    with hero_col:
        st.markdown(f"""
        <div class="cx-hero-wrap">
            <div class="cx-hero-label">Equity</div>
            <div class="cx-hero-value">${equity:,.2f}</div>
            <div class="{delta_class}">{arrow} ${day_pl:,.2f} ({day_pl_pct:+.2f}%) today</div>
            {ytd_line}
        </div>
        """, unsafe_allow_html=True)

    with rest_col:
        b, c = st.columns(2)
        b.metric("Cash", f"${float(account.cash):,.2f}")
        c.metric("Buying Power", f"${float(account.buying_power):,.2f}")

    st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
    try:
        render_equity_chart(get_equity_curve())
    except Exception as e:
        st.info(f"Equity chart unavailable: {e}")

except Exception as e:
    st.error(f"Unable to load account: {e}")

st.markdown('<hr class="cx-divider">', unsafe_allow_html=True)


# ---------- POSITIONS ----------

st.markdown('<div class="cx-section-label">📊 Open Positions</div>', unsafe_allow_html=True)

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

            card_class = "cx-card cx-card-good" if pl_pct >= 0 else "cx-card cx-card-bad"
            delta_class = "cx-delta-good" if pl_pct >= 0 else "cx-delta-bad"
            arrow = "▲" if pl_pct >= 0 else "▼"

            target_line = ""
            if target:
                target_line = f'<div class="cx-card-row">Stop: <b>${target["stop"]:.2f}</b> &nbsp;&nbsp; Target: <b>${target["target"]:.2f}</b></div>'

            st.markdown(f"""
            <div class="{card_class}">
                <div class="cx-card-title">{p.symbol}</div>
                <div class="cx-card-row">Qty: <b>{p.qty}</b> &nbsp;&nbsp; Entry: <b>${entry:.2f}</b> &nbsp;&nbsp; Current: <b>${current:.2f}</b></div>
                <div class="cx-card-row">Unrealized P/L: <span class="{delta_class}">{arrow} ${float(p.unrealized_pl):,.2f} ({pl_pct:+.2f}%)</span></div>
                {target_line}
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Unable to load positions: {e}")

st.markdown('<hr class="cx-divider">', unsafe_allow_html=True)


# ---------- PERFORMANCE / TRADE HISTORY ----------

st.markdown('<div class="cx-section-label">📈 Performance</div>', unsafe_allow_html=True)

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

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="cx-section-label">Recent Trades</div>', unsafe_allow_html=True)

    for t in reversed(completed[-10:]):
        pl = t.get("profit_loss", 0)
        card_class = "cx-card cx-card-good" if pl >= 0 else "cx-card cx-card-bad"
        delta_class = "cx-delta-good" if pl >= 0 else "cx-delta-bad"
        arrow = "▲" if pl >= 0 else "▼"

        st.markdown(f"""
        <div class="{card_class}">
            <div class="cx-card-row"><b>{t.get('symbol', '?')}</b> &nbsp; <span class="cx-muted">{t.get('date', '')}</span></div>
            <div class="cx-card-row">Buy: <b>${t.get('buy_price', 0):.2f}</b> &nbsp; Sell: <b>${t.get('sell_price', 0):.2f}</b> &nbsp; P/L: <span class="{delta_class}">{arrow} ${pl:,.2f}</span></div>
            <div class="cx-muted">{t.get('reason', '')}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No completed trades recorded yet.")

st.markdown('<hr class="cx-divider">', unsafe_allow_html=True)


# ---------- SCANNER ----------

st.markdown('<div class="cx-section-label">🔍 Market Scanner &mdash; top 5, refreshes every 5 min</div>', unsafe_allow_html=True)

try:
    top = get_scanner_results()[:5]

    cols = st.columns(len(top)) if top else []
    for col, s in zip(cols, top):
        with col:
            score = s["score"]
            if score >= 75:
                meter_color, track_color, badge_class = "#0ca30c", "rgba(12,163,12,0.15)", "cx-badge-good"
            elif score >= 50:
                meter_color, track_color, badge_class = "#fab219", "rgba(250,178,25,0.15)", "cx-badge-warn"
            else:
                meter_color, track_color, badge_class = "#898781", "rgba(137,135,129,0.15)", "cx-badge-muted"

            st.markdown(f"""
            <div class="cx-card">
                <div class="cx-card-title">{s['symbol']}</div>
                <div class="cx-card-row">Price: <b>${s['price']}</b> &nbsp; RSI: <b>{s['rsi']}</b></div>
                <div class="cx-card-row"><span class="{badge_class}">{s['bias']}</span></div>
                <div class="cx-meter-label"><span>Score</span><span>{score}/100</span></div>
                <div class="cx-meter-track" style="background:{track_color};"><div class="cx-meter-fill" style="width:{score}%; background:{meter_color};"></div></div>
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Scanner unavailable: {e}")

st.markdown('<div class="cx-caption" style="margin-top:1.5rem;">Cortex AI &mdash; Local Intelligence System</div>', unsafe_allow_html=True)
