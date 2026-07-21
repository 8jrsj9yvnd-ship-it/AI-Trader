import streamlit as st
from datetime import datetime
import random


st.set_page_config(
    page_title="Cortex AI",
    page_icon="🧠",
    layout="wide"
)


# ---------- STYLE ----------

st.markdown("""
<style>

.stApp {
    background-color: #05070d;
    color: white;
}

h1 {
    font-size: 60px;
    text-align: center;
}

.card {
    background: #101827;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #1f2937;
}

.status {
    font-size: 25px;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)


# ---------- HEADER ----------

st.title("🧠 CORTEX")

st.caption(
    "Autonomous Intelligence • Market Analysis • Trading System"
)


time = datetime.now().strftime("%H:%M:%S")


col1,col2,col3,col4 = st.columns(4)


with col1:
    st.metric(
        "SYSTEM",
        "ONLINE"
    )

with col2:
    st.metric(
        "VOICE",
        "ACTIVE"
    )

with col3:
    st.metric(
        "AI MODEL",
        "HERMES"
    )

with col4:
    st.metric(
        "TIME",
        time
    )


st.divider()


# ---------- AI CORE ----------


left,right = st.columns([1,2])


with left:

    st.subheader("🧠 Cortex Core")

    st.markdown("""
    <div class="card">

    Neural Engine:
    ONLINE

    Memory:
    CONNECTED

    Decision System:
    READY

    Risk Controls:
    ACTIVE

    </div>

    """, unsafe_allow_html=True)



with right:

    st.subheader("AI Thought Stream")

    thoughts = [
        "Analyzing market conditions...",
        "Scanning momentum...",
        "Evaluating risk...",
        "Reviewing previous trades..."
    ]

    for t in thoughts:
        st.write(
            "⚡ " + t
        )


st.divider()


# ---------- MARKET ----------


st.subheader("📈 Market Intelligence")


a,b,c = st.columns(3)


with a:
    st.metric(
        "SPY Trend",
        "BULLISH"
    )

with b:
    st.metric(
        "Market Risk",
        "LOW"
    )

with c:
    st.metric(
        "Scanner",
        "RUNNING"
    )



st.divider()


# ---------- TRADING ----------


st.subheader("💹 Trading Decision Engine")


stock = random.choice(
    ["AAPL","NVDA","MSFT","TSLA"]
)


st.markdown(
f"""
<div class="card">

<b>TOP OPPORTUNITY</b>

<br><br>

Stock:
{stock}

<br>

Confidence:
{random.randint(80,99)}%

<br>

Signal:
BUY

<br>

Risk:
LOW

</div>

""",
unsafe_allow_html=True
)


st.divider()


# ---------- CHAT ----------


st.subheader("🎙 Talk To Cortex")


message = st.chat_input(
    "Ask Cortex..."
)


if message:

    with st.chat_message("user"):
        st.write(message)

    with st.chat_message("assistant"):
        st.write(
            "Cortex is analyzing..."
        )

