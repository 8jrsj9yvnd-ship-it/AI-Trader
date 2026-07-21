from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


STOP_LOSS = 0.05      # 5%
TAKE_PROFIT = 0.10    # 10%


def manage_trades():

    positions = alpaca.get_all_positions()


    if len(positions) == 0:

        print("No positions to manage")
        return


    for position in positions:

        symbol = position.symbol

        entry = float(position.avg_entry_price)

        current = float(position.current_price)


        change = (current - entry) / entry


        print("\n", symbol)
        print("Entry:", entry)
        print("Current:", current)
        print("Return:", round(change * 100, 2), "%")


        if change <= -STOP_LOSS:

            print("STOP LOSS HIT")
            alpaca.close_position(symbol)


        elif change >= TAKE_PROFIT:

            print("TAKE PROFIT HIT")
            alpaca.close_position(symbol)


        else:

            print("Holding position")


manage_trades()