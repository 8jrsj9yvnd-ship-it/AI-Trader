import os
import ollama
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from cortex_learning import learning_summary

load_dotenv()

LOCAL_TZ = ZoneInfo("America/Los_Angeles")

# Real deployed URL -- do not let the model "answer" this from its own
# knowledge. It has no grounding for it and will hallucinate a plausible-
# looking fake (observed 2026-07-23: it invented the literal placeholder
# text "link_to_streamlit_app" as a real link when asked). Always inject
# this string into context instead.
DASHBOARD_URL = "https://ai-trader-mdaen73appykrcvqq2y5zgt.streamlit.app/"

alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


def get_alpaca_context():

    try:
        account = alpaca.get_account()
        positions = alpaca.get_all_positions()

        context = f"""
ALPACA ACCOUNT DATA:

Cash:
${account.cash}

Buying Power:
${account.buying_power}

Equity:
${account.equity}

OPEN POSITIONS:
"""

        if positions:
            for p in positions:
                context += f"""
{p.symbol}
Shares: {p.qty}
Entry Price: {p.avg_entry_price}
Current Price: {p.current_price}
Unrealized P/L: ${p.unrealized_pl}
"""
        else:
            context += "\nNo open positions."

        return context

    except Exception as e:
        return f"Unable to retrieve Alpaca data: {e}"


CORTEX_SYSTEM_PROMPT = (
    "You are Cortex, a helpful AI assistant and trading assistant. "
    "You can answer general questions, explain concepts, help with coding, "
    "and discuss investing and trading. Be concise, accurate, and conversational. "
    "Your training data has a fixed cutoff and does not include real-world events "
    "after that point -- for anything time-sensitive (current events, who holds an "
    "office, recent news) outside what's given to you in context below, say you "
    "don't have reliable up-to-date knowledge of it rather than guessing."
)


def get_time_context():
    now = datetime.now(LOCAL_TZ)
    return f"Current date/time: {now.strftime('%A, %B %d, %Y, %I:%M %p %Z')}"


def get_learning_context_summary():
    try:
        return learning_summary()
    except Exception as e:
        return f"Unable to retrieve trading performance history: {e}"


def ask_cortex_ollama(user_message, alpaca_context=None, model="hermes3:latest", history=None):
    """history: optional list of prior {"role": "user"|"assistant", "content": ...}
    turns for this conversation, oldest first, so Cortex has actual short-term
    memory of the exchange instead of answering each message from scratch."""

    if alpaca_context is None:
        alpaca_context = get_alpaca_context()

    messages = [{"role": "system", "content": CORTEX_SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({
        "role": "user",
        "content": (
            f"{get_time_context()}\n\n"
            f"Live dashboard URL (use this exact link if asked for the Streamlit "
            f"dashboard, web dashboard, or link -- never invent one): {DASHBOARD_URL}\n\n"
            f"Live Alpaca Account Data:\n\n{alpaca_context}\n\n"
            f"Trading Performance History:\n\n{get_learning_context_summary()}\n\n"
            f"User Message:\n{user_message}\n\n"
            "Use the data above when answering questions about the current date/time, "
            "profit, positions, trades, cash, portfolio, performance, or the dashboard link.\n\n"
            "Answer naturally as Cortex."
        ),
    })

    response = ollama.chat(model=model, messages=messages)

    return response["message"]["content"]
