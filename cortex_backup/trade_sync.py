from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os
import json


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


FILE = "trades.json"


def sync_trades():

    if not os.path.exists(FILE):
        print("No trade log found")
        return


    with open(FILE, "r") as f:
        trades = json.load(f)


    orders = alpaca.get_orders()


    for trade in trades:

        trade_id = trade.get("order_id")


        if not trade_id:
            continue


        for order in orders:

            if trade_id == str(order.id):

                trade["status"] = str(order.status)


                if order.filled_avg_price:

                    trade["filled_price"] = float(
                        order.filled_avg_price
                    )


    with open(FILE, "w") as f:
        json.dump(
            trades,
            f,
            indent=4
        )


    print("Trades synced")


sync_trades()