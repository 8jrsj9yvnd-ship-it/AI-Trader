from cortex import ask_cortex
from ranked_scanner import get_ranked_stocks


def get_market_analysis():

    stocks = get_ranked_stocks()

    if not stocks:
        return "No stocks found."


    best = stocks[0]


    prompt = f"""
You are Cortex Trading AI.

Analyze this opportunity:

Symbol:
{best['symbol']}

Price:
{best['price']}

RSI:
{best['rsi']}

Score:
{best['score']}

Give:

ACTION:
BUY / SELL / HOLD

CONFIDENCE:
0-100%

REASON:
Technical explanation

RISK:
LOW / MEDIUM / HIGH
"""


    response = ask_cortex(prompt)

    return response