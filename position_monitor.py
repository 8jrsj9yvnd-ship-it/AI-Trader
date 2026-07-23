from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from cortex_learning import log_trade
from position_targets import (
    get_target, clear_target,
    save_pending_exit, get_pending_exit, clear_pending_exit,
)
import config
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


STOP_LOSS_PERCENT = config.STOP_LOSS_PERCENT
TAKE_PROFIT_PERCENT = config.STOP_LOSS_PERCENT * config.TAKE_PROFIT_RATIO


def monitor_positions(session="REGULAR"):

    positions = alpaca.get_all_positions()


    if len(positions) == 0:

        print("No open positions")
        return


    for position in positions:

        symbol = position.symbol

        entry = float(position.avg_entry_price)

        current = float(position.current_price)


        change = (
            current - entry
        ) / entry


        print("\nPOSITION")
        print(symbol)
        print("Entry:", entry)
        print("Current:", current)
        print("Return:", round(change * 100, 2), "%")


        pending_order_id = get_pending_exit(symbol)

        if pending_order_id:

            # A close order is already in flight for this symbol -- check
            # whether it's actually filled instead of submitting another
            # one, and only log/clear the target once it's confirmed.
            resolve_pending_exit(symbol, pending_order_id, entry)
            continue


        target = get_target(symbol)

        if target:

            print("Stop:", target["stop"], "Target:", target["target"])

            if current <= target["stop"]:

                print("STOP LOSS TRIGGERED")

                close_position(symbol, session)

            elif current >= target["target"]:

                print("TAKE PROFIT TRIGGERED")

                close_position(symbol, session)


        else:

            if change <= -STOP_LOSS_PERCENT:

                print("STOP LOSS TRIGGERED")

                close_position(symbol, session)


            elif change >= TAKE_PROFIT_PERCENT:

                print("TAKE PROFIT TRIGGERED")

                close_position(symbol, session)



def close_position(symbol, session="REGULAR"):

    position = alpaca.get_open_position(symbol)

    qty = float(position.qty)
    current_price = float(position.current_price)

    try:
        if session == "REGULAR":

            result = alpaca.close_position(symbol)

        else:

            # Alpaca rejects market orders outside regular hours -- close
            # via a marketable limit instead, flagged extended_hours=True.
            limit_price = round(
                current_price * (1 - config.EXTENDED_HOURS_LIMIT_BUFFER),
                2
            )

            result = alpaca.submit_order(
                LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price,
                    extended_hours=True
                )
            )

    except Exception as e:
        print("SELL BLOCKED:", e)
        return

    # Don't log the trade or clear the target yet -- the order may not be
    # filled yet (especially the extended-hours limit case). Record it as
    # pending and let the next monitor_positions cycle confirm the fill
    # before touching learning history or dropping stop-loss tracking.
    save_pending_exit(symbol, str(result.id))

    print("CLOSE ORDER SUBMITTED:", result.id)


def resolve_pending_exit(symbol, order_id, entry_price):

    try:
        order = alpaca.get_order_by_id(order_id)
    except Exception as e:
        print("Could not check exit order status:", e)
        return

    if order.status == OrderStatus.FILLED:

        fill_price = float(order.filled_avg_price)
        qty = float(order.filled_qty)
        profit_loss = (fill_price - entry_price) * qty

        log_trade(
            symbol,
            entry_price,
            fill_price,
            profit_loss,
            "Exited by Cortex risk management"
        )

        clear_target(symbol)
        clear_pending_exit(symbol)

        print("CLOSED:", symbol, "P/L:", round(profit_loss, 2))
        print("LEARNING UPDATED")

    elif order.status in (
        OrderStatus.CANCELED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    ):

        # Exit never went through -- clear the pending flag so the next
        # cycle re-evaluates the stop/target trigger and retries.
        print(f"Exit order for {symbol} ended as {order.status}, will retry")
        clear_pending_exit(symbol)

    else:

        print(f"Exit order for {symbol} still {order.status}, waiting...")


if __name__ == "__main__":
    monitor_positions()