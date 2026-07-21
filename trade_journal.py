import json
from datetime import datetime
import os


FILE = "trades.json"


def log_trade(data):

    data["time"] = str(datetime.now())

    if os.path.exists(FILE):

        with open(FILE, "r") as f:
            trades = json.load(f)

    else:
        trades = []


    trades.append(data)


    with open(FILE, "w") as f:
        json.dump(
            trades,
            f,
            indent=4
        )


    print("Trade logged")


example_trade = {
    "symbol": "AAPL",
    "action": "BUY",
    "confidence": 95,
    "reason": "Strong trend above moving averages",
    "entry": 327.50,
    "stop_loss": 311.12,
    "take_profit": 360.25
}


log_trade(example_trade)