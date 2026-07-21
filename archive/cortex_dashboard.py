import streamlit as st
from datetime import datetime
from ranked_scanner import get_ranked_stocks


st.set_page_config(
    page_title="Cortex Trading AI",
    page_icon="🧠",
    layout="wide"
)


# ---------- STYLE ----------

st.markdown("""
<style>

.stApp {
    background-color:#05070d;
    color:white;
}

h1 {
    text-align:center;
    font-size:55px;
}

.card {
    background:#111827;
    padding:20px;
    border-radius:15px;
    border:1px solid #374151;
}

</style>
""", unsafe_allow_html=True)



# ---------- HEADER ----------

st.title("🧠 CORTEX TRADING AI")

st.caption(
    "Autonomous Market Intelligence & Trading System"
)


time = datetime.now().strftime("%H:%M:%S")


a,b,c,d = st.columns(4)


with a:
    st.metric(
        "SYSTEM",
        "ONLINE"
    )

with b:
    st.metric(
        "AI ENGINE",
        "HERMES"
    )

with c:
    st.metric(
        "SCANNER",
        "ACTIVE"
    )

with d:
    st.metric(
        "TIME",
        time
    )


st.divider()



# ---------- MARKET SCANNER ----------


st.header("🔍 Market Scanner")


try:

    stocks = get_ranked_stocks()


    if stocks:

        for stock in stocks[:5]:

            st.markdown(
            f"""
            <div class="card">

            <h3>{stock['symbol']}</h3>

            Score:
            {stock['score']}

            <br>

            Price:
            ${stock['price']}

            <br>

            RSI:
            {stock['rsi']}

            </div>

            <br>

            """,
            unsafe_allow_html=True
            )


except Exception as e:

    st.error(e)



st.divider()



# ---------- CORTEX DECISION ----------


st.header("🤖 Cortex Decision Engine")


st.markdown(
"""
<div class="card">

Waiting for AI analysis...

<br><br>

Signal:
WAITING

<br>

Confidence:
--

<br>

Risk:
--

</div>

""",
unsafe_allow_html=True
)



st.divider()



# ---------- CHAT ----------


st.header("🎙 Cortex Communication")


message = st.chat_input(
"Ask Cortex..."
)


if message:

    st.write(
        "You:",
        message
    )

    st.write(
        "Cortex:",
        "Analyzing request..."
    )