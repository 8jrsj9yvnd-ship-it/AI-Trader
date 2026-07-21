from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from cortex_learning import log_trade
from position_targets import get_target, clear_target
import config
from alpaca.trading.enums import OrderSide, TimeInForce
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


def monitor_positions():

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


        target = get_target(symbol)

        if target:

            print("Stop:", target["stop"], "Target:", target["target"])

            if current <= target["stop"]:

                print("STOP LOSS TRIGGERED")

                close_position(symbol)

            elif current >= target["target"]:

                print("TAKE PROFIT TRIGGERED")

                close_position(symbol)


        else:

            if change <= -STOP_LOSS_PERCENT:

                print("STOP LOSS TRIGGERED")

                close_position(symbol)


            elif change >= TAKE_PROFIT_PERCENT:

                print("TAKE PROFIT TRIGGERED")

                close_position(symbol)



def close_position(symbol):

    position = alpaca.get_open_position(symbol)

    entry_price = float(position.avg_entry_price)
    qty = float(position.qty)

    try:
        result = alpaca.close_position(symbol)

    except Exception as e:
        print("SELL BLOCKED:", e)
        return
    current_price = float(position.current_price)

    profit_loss = (current_price - entry_price) * qty

    log_trade(
        symbol,
        entry_price,
        current_price,
        profit_loss,
        "Exited by Cortex risk management"
    )

    clear_target(symbol)

    print("CLOSED:")
    print(result)
    print("LEARNING UPDATED")


if __name__ == "__main__":
    monitor_positions()