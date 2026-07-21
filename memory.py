import json
import os
from datetime import datetime

MEMORY_FILE = "trade_memory.json"


def save_trade(stock, action, result, lesson):
    trades = []

    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as file:
            trades = json.load(file)

    trades.append({
        "date": str(datetime.now()),
        "stock": stock,
        "action": action,
        "result": result,
        "lesson": lesson
    })

    with open(MEMORY_FILE, "w") as file:
        json.dump(trades, file, indent=4)


def read_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as file:
            return json.load(file)

    return []