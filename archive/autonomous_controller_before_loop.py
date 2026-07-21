from daily_risk import check_daily_loss
from trade_logger import log_trade
from market_filter import market_is_good
from stock_scanner import analyze_stock, stocks
from stock_ranker import score_stock
from risk_manager import calculate_position_size
from safety_controller import check_safety

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from dotenv import load_dotenv

import ollama
import json
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


def ask_hermes(candidates):

    prompt = f"""
You are a trading analyst.

Analyze these stock candidates:

{json.dumps(candidates, indent=2)}

Choose the BEST opportunity.

Return ONLY JSON:

{{
"symbol": "TICKER",
"signal": "BUY or HOLD",
"confidence": 0-100,
"reason": "explanation",
"risk": "LOW, MEDIUM, HIGH"
}}
"""

    response = ollama.chat(
        model="hermes3:latest",
        format="json",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return json.loads(
        response["message"]["content"]
    )


# =====================
# RISK CHECK
# =====================

allowed_risk, risk_message = check_daily_loss()

print("\nRISK CHECK:")
print(risk_message)


if not allowed_risk:
    print("TRADING STOPPED")
    exit()


# =====================
# MARKET FILTER
# =====================

good_market, reason = market_is_good()

print("\nMARKET FILTER:")
print(reason)


if not good_market:
    print("TRADING STOPPED")
    exit()



# =====================
# SCAN MARKET
# =====================

results = []


for symbol in stocks:

    try:

        data = analyze_stock(symbol)

        data["score"] = score_stock(data)

        results.append(data)


    except Exception as e:

        print(symbol, "ERROR", e)



ranked = sorted(
    results,
    key=lambda x: x["score"],
    reverse=True
)


top_five = ranked[:5]


print("\nTOP 5:")

for stock in top_five:

    print(
        stock["symbol"],
        stock["score"]
    )



# =====================
# HERMES DECISION
# =====================

decision = ask_hermes(top_five)


print("\nAI DECISION:")
print(decision)


symbol = decision["symbol"]


selected = next(
    x for x in top_five
    if x["symbol"] == symbol
)



# =====================
# SAFETY + EXECUTION
# =====================

if decision["signal"] == "BUY" and decision["confidence"] >= 70:


    allowed, reason = check_safety(symbol)


    print("\nSAFETY:")
    print(reason)


    if allowed:


        clock = alpaca.get_clock()


        if not clock.is_open:

            print("MARKET CLOSED - NO ORDER")
            exit()



        account = alpaca.get_account()


        risk = calculate_position_size(
            float(account.equity),
            float(selected["price"])
        )


        shares = min(
            risk["shares"],
            5
        )


        print("Shares:", shares)



        entry_price = float(
            selected["price"]
        )


        take_profit = round(
            entry_price * 1.10,
            2
        )


        stop_loss = round(
            entry_price * 0.95,
            2
        )


        print("Take Profit:", take_profit)
        print("Stop Loss:", stop_loss)



        order = MarketOrderRequest(
            symbol=symbol,
            qty=shares,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )


        result = alpaca.submit_order(order)



        print("ORDER SENT")
        print(result.id)



        log_trade({

            "symbol": symbol,
            "shares": shares,
            "entry": entry_price,
            "confidence": decision["confidence"],
            "reason": decision["reason"],
            "order_id": str(result.id),
            "status": "OPEN",
            "take_profit": take_profit,
            "stop_loss": stop_loss

        })


    else:

        print("TRADE BLOCKED")


else:

    print("NO TRADE")