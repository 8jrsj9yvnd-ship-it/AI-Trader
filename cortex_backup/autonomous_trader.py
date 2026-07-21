from ranked_scanner import get_ranked_stocks
from cortex import ask_cortex
from execute_trade import execute_trade
from safety_controller import check_safety


def get_cortex_decision(stock):

    prompt = f"""
You are Cortex Trading AI.

Analyze this trade opportunity.

Symbol:
{stock['symbol']}

Price:
{stock['price']}

Score:
{stock['score']}

RSI:
{stock['rsi']}


Respond exactly:

ACTION:
BUY or HOLD

CONFIDENCE:
number 0-100

REASON:
short explanation

RISK:
LOW, MEDIUM, HIGH
"""

    return ask_cortex(prompt)



def run_cortex_trader():

    print("\n===== CORTEX AUTONOMOUS TRADER =====\n")


    stocks = get_ranked_stocks()


    if not stocks:
        print("No opportunities found.")
        return


    target = stocks[0]


    print("TOP STOCK:")
    print(target)


    decision = get_cortex_decision(target)


    print("\nCORTEX DECISION:")
    print(decision)


    if "BUY" not in decision.upper():

        print("\nCortex decided not to trade.")

        return



    approved, reason = check_safety(
        target["symbol"]
    )


    print("\nSAFETY CHECK:")
    print(reason)


    if not approved:

        print("TRADE BLOCKED")

        return



    result = execute_trade(
        target["symbol"],
        target["price"]
    )


    print("\nORDER RESULT:")
    print(result)



if __name__ == "__main__":

    run_cortex_trader()