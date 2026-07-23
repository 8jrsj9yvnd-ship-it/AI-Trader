from daily_risk import check_daily_loss
from trade_logger import log_trade as record_trade
from market_filter import market_is_good
from market_hours import get_session
from stock_scanner import analyze_stock, stocks
from risk_manager import calculate_position_size
from safety_controller import check_safety
from position_monitor import monitor_positions
from position_targets import save_target
from instance_lock import acquire_lock, is_locked
from heartbeat import write_heartbeat
import config

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from dotenv import load_dotenv

import os
import time
from cortex_learning import log_trade as log_learning
import sys
from datetime import datetime

# stdout/stderr are redirected to log files when launched by start_cortex.ps1,
# which makes Python fall back to full block-buffering instead of line
# buffering -- prints (including error output) can sit invisible in the
# buffer for a long time instead of showing up in the log promptly.
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


load_dotenv()


# ===============================
# SINGLE INSTANCE PROTECTION
# ===============================

if not acquire_lock("autonomous_controller"):

    print("Cortex is already running. Exiting.")

    sys.exit(0)



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



def run_cycle(session="REGULAR"):

    global scan_count

    scan_count += 1


    print("\n")
    print("="*40)
    print("CORTEX SCAN #",scan_count,f"[{session}]")
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

            results.append(data)


        except Exception as e:

            print(symbol,e)



    ranked = sorted(

        results,

        key=lambda x:x["score"],

        reverse=True

    )


    print("\nTOP PICKS")

    for s in ranked[:5]:

        print(
            s["symbol"],
            "| Score:",
            s["score"],
            "| RSI:",
            s["rsi"],
            "| Price:",
            s["price"]
        )


    # Entry criteria here must match backtester_entry_sweep.py's run() exactly
    # (score >= MIN_ENTRY_SCORE, rsi <= 75) plus the separately-validated
    # volume_strength gate -- these thresholds are the actual walk-forward-
    # backtested edge documented in config.py. Every candidate that clears
    # them gets evaluated for entry this cycle, not just a single top pick,
    # since the portfolio-level backtest showed returns improving monotonically
    # as concurrent positions rose toward MAX_OPEN_POSITIONS.
    candidates = [
        s for s in ranked
        if s["score"] >= config.MIN_ENTRY_SCORE
        and s["rsi"] <= 75
        and s["volume_strength"] >= config.MIN_VOLUME_STRENGTH
    ]

    if not candidates:
        print("\nNo candidates meet entry criteria this cycle")
        return

    print(f"\n{len(candidates)} candidate(s) meet entry criteria")

    entries = 0

    for selected in candidates:

        if enter_position(selected, session):
            entries += 1

    print(f"\n{entries} order(s) submitted this cycle")


def enter_position(selected, session):
    """Attempt to open a position in `selected` (a scored candidate dict from
    analyze_stock). Returns True if an order was submitted."""

    symbol = selected["symbol"]

    positions = [
        p.symbol
        for p in alpaca.get_all_positions()
    ]

    if symbol in positions:
        print(symbol, "-- already holding")
        return False

    allowed, reason = check_safety(symbol)

    print(f"\n{symbol} SAFETY:", reason)

    if not allowed:
        return False

    account = alpaca.get_account()

    price = float(selected["price"])

    sizing = calculate_position_size(
        float(account.equity),
        price,
        atr=selected.get("atr")
    )

    shares = min(
        sizing["shares"],
        config.MAX_SHARES_PER_TRADE
    )

    if shares <= 0:
        return False

    if session == "REGULAR":

        order = MarketOrderRequest(
            symbol=symbol,
            qty=shares,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )

    else:

        # Alpaca rejects market orders outside regular hours -- use a
        # marketable limit instead, flagged extended_hours=True.
        limit_price = round(
            price * (1 + config.EXTENDED_HOURS_LIMIT_BUFFER),
            2
        )

        order = LimitOrderRequest(
            symbol=symbol,
            qty=shares,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price,
            extended_hours=True
        )

    try:
        result = alpaca.submit_order(order)
    except Exception as e:
        print(symbol, "BUY BLOCKED:", e)
        return False

    reason = selected.get("reason", "")

    log_learning(
        symbol,
        float(result.filled_avg_price) if result.filled_avg_price else 0,
        0,
        0,
        reason
    )

    save_target(
        symbol,
        sizing["stop_loss"],
        sizing["take_profit"]
    )

    print("ORDER SENT:", symbol, result.id)

    record_trade({
        "symbol": symbol,
        "shares": shares,
        "entry": price,
        "confidence": selected["score"],
        "reason": reason,
        "order_id": str(result.id),
        "status": "OPEN"
    })

    return True



# ===============================
# START CORTEX
# ===============================


banner()

print(
    "CORTEX STARTED"
)


system_check()


HEARTBEAT_INTERVAL = 60
_last_heartbeat = 0


while True:


    try:

        now = time.time()
        if now - _last_heartbeat >= HEARTBEAT_INTERVAL:
            write_heartbeat(True, is_locked("cortex_discord"))
            _last_heartbeat = now

        session = get_session()

        tradeable = (
            session == "REGULAR"
            or (config.ENABLE_EXTENDED_HOURS and session in ("PRE_MARKET", "AFTER_HOURS"))
        )

        if tradeable:


            monitor_positions(session)

            run_cycle(session)

            show_positions()


            print(
                f"\nCortex alive [{session}]. Next scan in 60 seconds..."
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