from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


STOP_LOSS_PERCENT = 0.05
TAKE_PROFIT_PERCENT = 0.10


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


        if change <= -STOP_LOSS_PERCENT:

            print("STOP LOSS TRIGGERED")

            close_position(symbol)


        elif change >= TAKE_PROFIT_PERCENT:

            print("TAKE PROFIT TRIGGERED")

            close_position(symbol)



def close_position(symbol):

    result = alpaca.close_position(symbol)

    print("CLOSED:")
    print(result)


monitor_positions()