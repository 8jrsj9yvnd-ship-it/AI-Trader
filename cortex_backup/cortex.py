import ollama
import json
import os

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

from stock_scanner import analyze_stock, stocks
from stock_ranker import score_stock


load_dotenv()


MEMORY_FILE = "cortex_memory.json"
STARTING_CAPITAL = 100000


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


SYSTEM = """
You are Cortex.

You are an autonomous trading AI command center.

Your purpose:
- Analyze real market opportunities
- Explain trading decisions
- Review portfolio performance
- Discuss risk

Never invent companies or fake stock data.

When analyzing a stock include:
- Trend
- Momentum
- Technical picture
- Risk
- Reward potential
- Reasoning

Speak as Cortex.

Technical accuracy rules:
- RSI below 30 = potentially oversold
- RSI above 70 = potentially overbought
- RSI between 50-70 = positive momentum range
- Never describe high RSI as a low point
- Never invent company information or fundamentals
- Only use data provided by the system
"""


def load_memory():

    if os.path.exists(MEMORY_FILE):

        with open(MEMORY_FILE, "r") as f:
            return json.load(f)

    return []



def save_memory(memory):

    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)



def scan_market():

    results = []

    for symbol in stocks:

        try:

            data = analyze_stock(symbol)

            data["score"] = score_stock(data)

            results.append(data)

        except Exception as e:

            print(symbol, "ERROR:", e)


    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:5]



def portfolio():

    account = alpaca.get_account()

    positions = alpaca.get_all_positions()

    value = float(account.equity)

    profit = value - STARTING_CAPITAL

    percent = (profit / STARTING_CAPITAL) * 100


    return {
        "starting_capital": STARTING_CAPITAL,
        "current_value": value,
        "profit": profit,
        "return_percent": percent,
        "positions": positions
    }



def orders():

    from alpaca.trading.requests import GetOrdersRequest

    request = GetOrdersRequest(
        limit=10
    )

    return alpaca.get_orders(request)



def ask_cortex(prompt):

    response = ollama.chat(
        model="hermes3:latest",
        messages=[
            {
                "role": "system",
                "content": SYSTEM
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )


    answer = response["message"]["content"]


    memory = load_memory()

    memory.append(
        {
            "prompt": prompt,
            "response": answer
        }
    )

    save_memory(memory)


    return answer



def analyze_stock_with_cortex(symbol):

    prompt = f"""
Analyze {symbol}.

Provide:

ACTION:
BUY / SELL / HOLD

CONFIDENCE:
0-100%

TREND:

MOMENTUM:

RISK:

REASON:
"""


    return ask_cortex(prompt)



memory = load_memory()