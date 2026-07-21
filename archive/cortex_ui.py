import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Cortex AI",
    page_icon="🧠",
    layout="wide"
)

# Header
st.title("🧠 Cortex AI")
st.subheader("Personal Trading Intelligence System")

st.divider()

# Status panel
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="AI Status",
        value="ONLINE"
    )

with col2:
    st.metric(
        label="Market",
        value="OPEN"
    )

with col3:
    st.metric(
        label="Time",
        value=datetime.now().strftime("%H:%M:%S")
    )


st.divider()

# Cortex conversation
st.header("Talk to Cortex")

user_input = st.text_input(
    "Message Cortex:"
)

if user_input:

    st.write("🧠 Cortex:")
    
    # Temporary response
    st.success(
        "I received: " + user_input
    )


st.divider()

# Trading section
st.header("Trading Overview")

col1, col2 = st.columns(2)

with col1:
    st.write("📈 Market Analysis")
    st.write(
        """
        SPY Trend:
        Positive

        Risk:
        Low

        Scanner:
        Running
        """
    )

with col2:
    st.write("💼 Portfolio")

    st.write(
        """
        Positions:
        None

        Buying Power:
        Connected

        Broker:
        Alpaca Paper
        """
    )


st.divider()

st.caption(
    "Cortex AI — Local Intelligence System"
)