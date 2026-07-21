import json
import os
from datetime import datetime


FILE = "trades.json"


def log_trade(data):

    if os.path.exists(FILE):

        with open(FILE, "r") as f:
            trades = json.load(f)

    else:
        trades = []


    data["time"] = str(datetime.now())

    trades.append(data)


    with open(FILE, "w") as f:
        json.dump(
            trades,
            f,
            indent=4
        )


    print("Trade recorded")