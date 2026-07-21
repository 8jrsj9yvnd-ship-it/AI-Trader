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
from datetime import datetime


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


scan_count = 0


def banner():

    print("""
========================================
        CORTEX AUTONOMOUS TRADER
========================================
""")


def system_check():

    print("\nSYSTEM CHECK")
    print("----------------")

    try:
        account = alpaca.get_account()

        print("Alpaca: ONLINE")
        print("Paper Trading: ENABLED")
        print("Account Status:", account.status)
        print("Cash:", account.cash)
        print("Buying Power:", account.buying_power)

    except Exception as e:

        print("Alpaca ERROR:", e)


    try:

        ollama.list()

        print("Ollama: ONLINE")

    except Exception as e:

        print("Ollama ERROR:", e)



def countdown():

    clock = alpaca.get_clock()

    now = datetime.now(
        clock.next_open.tzinfo
    )

    seconds = int(
        (clock.next_open - now).total_seconds()
    )


    if seconds < 0:
        seconds = 0


    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60


    print(
        f"\rMARKET OPENS IN "
        f"{hours:02}:{minutes:02}:{secs:02}",
        end=""
    )



def ask_cortex(candidates):

    prompt = f"""
You are Cortex, an autonomous trading intelligence system.

Analyze these candidates:

{json.dumps(candidates, indent=2)}

Pick the strongest trade.

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
                "role":"user",
                "content":prompt
            }
        ]
    )


    return json.loads(
        response["message"]["content"]
    )



def show_positions():

    positions = alpaca.get_all_positions()

    print("\nCURRENT POSITIONS")

    if not positions:

        print("None")

        return


    for p in positions:

        print(
            p.symbol,
            "Qty:",
            p.qty,
            "P/L:",
            p.unrealized_pl
        )



def run_cycle():

    global scan_count

    scan_count += 1


    print("\n")
    print("="*40)
    print("CORTEX SCAN #", scan_count)
    print(datetime.now())
    print("="*40)


    allowed, message = check_daily_loss()

    print("\nRISK:")
    print(message)


    if not allowed:

        print("RISK BLOCK")

        return



    good, reason = market_is_good()

    print("\nMARKET FILTER:")
    print(reason)


    if not good:

        print("MARKET BLOCK")

        return



    results=[]


    print("\nSCANNING STOCKS...")


    for symbol in stocks:

        try:

            data = analyze_stock(symbol)

            data["score"] = score_stock(data)

            results.append(data)


        except Exception as e:

            print(symbol,e)



    ranked = sorted(

        results,

        key=lambda x:x["score"],

        reverse=True

    )


    top = ranked[:5]


    print("\nTOP PICKS")


    for s in top:

        print(
f"""
{s['symbol']}
Price: ${s['price']}
SMA20: {s['sma20']}
SMA50: {s['sma50']}
RSI: {s['rsi']}
Score: {s['score']}
"""
        )



    decision = ask_cortex(top)


    print("\nCORTEX DECISION")

    print(
        json.dumps(
            decision,
            indent=2
        )
    )


    if decision["signal"] != "BUY":

        print("NO TRADE")

        return


    if decision["confidence"] < 70:

        print("LOW CONFIDENCE")

        return



    symbol = decision["symbol"]


    positions = [
        p.symbol
        for p in alpaca.get_all_positions()
    ]


    if symbol in positions:

        print(
            "Already holding",
            symbol
        )

        return



    allowed, reason = check_safety(symbol)


    print("\nSAFETY:")
    print(reason)


    if not allowed:

        return



    selected = next(

        x for x in top

        if x["symbol"] == symbol

    )


    account = alpaca.get_account()


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
        "\nBUY ORDER:",
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

        "symbol":symbol,

        "shares":shares,

        "entry":price,

        "confidence":decision["confidence"],

        "reason":decision["reason"],

        "order_id":str(result.id),

        "status":"OPEN"

    })



banner()

system_check()


while True:

    try:

        clock = alpaca.get_clock()


        if clock.is_open:

            run_cycle()

            show_positions()


            print(
                "\nCortex alive. Next scan in 60 seconds..."
            )


            time.sleep(60)


        else:

            countdown()

            time.sleep(1)


    except Exception as e:

        print(
            "\nCORTEX ERROR:",
            e
        )

        time.sleep(30)