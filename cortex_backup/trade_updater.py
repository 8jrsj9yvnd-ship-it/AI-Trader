import json
import os


FILE = "trades.json"


def update_closed_trade(symbol, exit_price):

    if not os.path.exists(FILE):
        return


    with open(FILE, "r") as f:
        trades = json.load(f)


    for trade in trades:

        if (
            trade["symbol"] == symbol
            and trade["status"] == "OPEN"
        ):

            entry = trade["entry"]
            shares = trade["shares"]


            profit = (
                exit_price - entry
            ) * shares


            trade["exit"] = exit_price
            trade["profit"] = round(profit, 2)
            trade["status"] = "CLOSED"


    with open(FILE, "w") as f:
        json.dump(
            trades,
            f,
            indent=4
        )


    print("Trade updated")