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
import time


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


def ask_hermes(candidates):

    prompt = f"""
You are Cortex, an autonomous trading system.

Analyze these stocks:

{json.dumps(candidates, indent=2)}

Choose the strongest opportunity.

Consider:
- Trend
- Momentum
- RSI
- Risk
- Price strength

Return ONLY JSON:

{{
"symbol":"TICKER",
"signal":"BUY or HOLD",
"confidence":0-100,
"reason":"why",
"risk":"LOW MEDIUM HIGH"
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


def get_positions():

    positions = alpaca.get_all_positions()

    return [
        p.symbol
        for p in positions
    ]


def run_cycle():

    print("\n==============================")
    print("CORTEX SCAN")
    print("==============================")


    allowed, msg = check_daily_loss()

    print(msg)

    if not allowed:
        print("Risk limit reached")
        return



    good, reason = market_is_good()

    print("\nMARKET FILTER:")
    print(reason)

    if not good:
        print("Market conditions poor")
        return



    results = []


    print("\nSCANNING:")


    for symbol in stocks:

        try:

            data = analyze_stock(symbol)

            data["score"] = score_stock(data)

            results.append(data)


        except Exception as e:

            print(symbol, "ERROR:", e)



    if not results:

        print("No stocks found")
        return



    ranked = sorted(
        results,
        key=lambda x:x["score"],
        reverse=True
    )


    top = ranked[:5]


    print("\nTOP PICKS WITH STATS")

    for s in top:

        print(
f"""
{s["symbol"]}
----------------
Price: ${s["price"]}
SMA20: {s["sma20"]}
SMA50: {s["sma50"]}
RSI: {s["rsi"]}
Score: {s["score"]}
"""
        )



    decision = ask_hermes(top)


    print("\nCORTEX DECISION")
    print(
        json.dumps(
            decision,
            indent=2
        )
    )



    if decision["signal"] != "BUY":

        print("NO BUY SIGNAL")
        return



    if decision["confidence"] < 70:

        print("CONFIDENCE TOO LOW")
        return



    symbol = decision["symbol"]



    if symbol in get_positions():

        print(
            "Already holding",
            symbol
        )

        return



    selected = next(
        (
            x for x in top
            if x["symbol"] == symbol
        ),
        None
    )


    if not selected:

        print("AI selected invalid stock")
        return



    allowed, reason = check_safety(symbol)


    print("\nSAFETY:")
    print(reason)


    if not allowed:

        print("TRADE BLOCKED")
        return



    account = alpaca.get_account()


    print(
        "Account Equity:",
        account.equity
    )


    price = float(
        selected["price"]
    )


    sizing = calculate_position_size(
        float(account.equity),
        price
    )


    shares = min(
        sizing["shares"],
        5
    )


    print(
        "BUYING:",
        shares,
        symbol
    )


    order = MarketOrderRequest(
        symbol=symbol,
        qty=shares,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )


    result = alpaca.submit_order(order)


    print(
        "ORDER SENT:",
        result.id
    )


    log_trade({

        "symbol": symbol,
        "shares": shares,
        "entry": price,
        "confidence": decision["confidence"],
        "reason": decision["reason"],
        "order_id": str(result.id),
        "status": "OPEN"

    })


print("""
================================
      CORTEX ONLINE
================================
""")


while True:

    clock = alpaca.get_clock()


    if clock.is_open:

        run_cycle()

        print(
            "\nWaiting 60 seconds..."
        )

        time.sleep(60)


    else:

        print(
            "Market closed. Next open:",
            clock.next_open
        )

        time.sleep(300)