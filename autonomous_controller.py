from daily_risk import check_daily_loss
from trade_logger import log_trade as record_trade
from market_filter import market_is_good
from stock_scanner import analyze_stock, stocks
from risk_manager import calculate_position_size
from safety_controller import check_safety
from position_monitor import monitor_positions
import config

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from dotenv import load_dotenv

import ollama
import json
import os
import time
from cortex_learning import log_trade as log_learning, learning_summary, get_learning_context
import sys
import psutil
from datetime import datetime


load_dotenv()


# ===============================
# SINGLE INSTANCE PROTECTION
# ===============================

def already_running():

    current_pid = os.getpid()

    for process in psutil.process_iter(
        ["pid", "cmdline"]
    ):

        try:

            if process.info["pid"] == current_pid:
                continue

            cmd = " ".join(
                process.info["cmdline"] or []
            )

            if (
                "autonomous_controller.py" in cmd
                and "D:\\AI-Trader\\venv\\Scripts\\python.exe" in cmd
            ):
                return True

        except:
            pass

    return False



# Single instance check disabled
# Duplicate launchers removed



# ===============================
# ALPACA
# ===============================

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
        print("Cash:", account.cash)
        print("Buying Power:", account.buying_power)

    except Exception as e:

        print(
            "Alpaca ERROR:",
            e
        )


    try:

        ollama.list()

        print("Ollama: ONLINE")

    except Exception as e:

        print(
            "Ollama ERROR:",
            e
        )



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


    h = seconds // 3600
    m = (seconds % 3600)//60
    s = seconds % 60


    print(
    f"MARKET OPENS IN {h:02}:{m:02}:{s:02}"
)



def ask_cortex(candidates):

    learning = get_learning_context()

    prompt = f"""

You are Cortex trading AI.

Previous trading performance:

{learning}

Use this history to improve future decisions.

Rank these stocks.

Only choose BUY if:

- Score above 80
- RSI is healthy
- Trend is positive
- Risk is acceptable


Candidates:

{json.dumps(candidates,indent=2)}


Return JSON only:

{{
"symbol":"TICKER",
"signal":"BUY or HOLD",
"confidence":0-100,
"reason":"reason",
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
    print("CORTEX SCAN #",scan_count)
    print(datetime.now())
    print("="*40)


    allowed,message = check_daily_loss()

    print("\nRISK:")
    print(message)


    if not allowed:

        print("RISK BLOCK")
        return



    good,reason = market_is_good()


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

            data["score"] = data["score"]

            results.append(data)


        except Exception as e:

            print(symbol,e)



    ranked = sorted(

        results,

        key=lambda x:x["score"],

        reverse=True

    )


    top = ranked[:3]


    print("\nTOP PICKS")


    for s in top:

        print(
            s["symbol"],
            "| Score:",
            s["score"],
            "| RSI:",
            s["rsi"],
            "| Price:",
            s["price"]
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
        return


    if decision["confidence"] < 80:
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



    selected = next(

        x for x in top

        if x["symbol"] == symbol

    )


    if selected["rsi"] > 75:

        print(
            "SKIPPING RSI TOO HIGH"
        )

        return
    if selected["score"] < 75:

        print(
            "SKIPPING SCORE TOO LOW"
        )

        return


    if selected["volume_strength"] < 1.0:

        print(
            "SKIPPING WEAK VOLUME"
        )

        return



    allowed,reason = check_safety(symbol)


    print("\nSAFETY:")
    print(reason)


    if not allowed:
        return



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

        config.MAX_SHARES_PER_TRADE

    )


    if shares <= 0:
        return



    order = MarketOrderRequest(

        symbol=symbol,

        qty=shares,

        side=OrderSide.BUY,

        time_in_force=TimeInForce.DAY

    )


    result = alpaca.submit_order(order)

    if result:
        log_learning(
            symbol,
            float(result.filled_avg_price) if result.filled_avg_price else 0,
            0,
            0,
            decision["reason"]
        )


    print(
        "ORDER SENT:",
        result.id
    )


    record_trade({

        "symbol":symbol,

        "shares":shares,

        "entry":price,

        "confidence":decision["confidence"],

        "reason":decision["reason"],

        "order_id":str(result.id),

        "status":"OPEN"

    })



# ===============================
# START CORTEX
# ===============================


banner()

print(
    "CORTEX STARTED"
)


system_check()



while True:


    try:


        clock = alpaca.get_clock()


        if clock.is_open:


            monitor_positions()

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