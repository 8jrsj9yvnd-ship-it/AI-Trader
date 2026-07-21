import json
import os


FILE = "trades.json"


def performance_report():

    if not os.path.exists(FILE):

        print("No trade history found")
        return


    with open(FILE, "r") as f:
        trades = json.load(f)


    closed = [
        t for t in trades
        if t.get("status") == "CLOSED"
    ]


    if len(closed) == 0:

        print("No closed trades yet")
        return


    total_profit = 0
    wins = 0
    losses = 0


    for trade in closed:

        profit = float(trade.get("profit", 0))

        total_profit += profit


        if profit > 0:
            wins += 1

        else:
            losses += 1


    win_rate = (
        wins / len(closed)
    ) * 100


    print("\n===== AI TRADER REPORT =====")
    print("Total Trades:", len(closed))
    print("Wins:", wins)
    print("Losses:", losses)
    print("Win Rate:", round(win_rate, 2), "%")
    print("Total Profit/Loss: $", round(total_profit, 2))


performance_report()