import os
import ollama
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

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
    "and discuss investing and trading. Be concise, accurate, and conversational."
)


def ask_cortex_ollama(user_message, alpaca_context=None, model="hermes3:latest"):

    if alpaca_context is None:
        alpaca_context = get_alpaca_context()

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": CORTEX_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Live Alpaca Account Data:\n\n{alpaca_context}\n\n"
                    f"User Message:\n{user_message}\n\n"
                    "Use the account data above when answering questions about profit, positions, "
                    "trades, cash, portfolio, performance.\n\nAnswer naturally as Cortex."
                ),
            },
        ],
    )

    return response["message"]["content"]
