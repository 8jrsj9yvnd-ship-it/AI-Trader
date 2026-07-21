import json
import os
from datetime import datetime

MEMORY_FILE = "cortex_memory.json"


def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return []

    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(memory):

    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)


def log_trade(symbol, buy_price, sell_price, profit_loss, reason):

    memory = load_memory()

    memory.append(
        {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "profit_loss": profit_loss,
            "reason": reason
        }
    )

    save_memory(memory)


def learning_summary():

    memory = load_memory()

    if len(memory) == 0:
        return "No trades have been recorded yet."

    # Ignore older memory entries without profit/loss data
    valid_trades = [
        trade for trade in memory
        if "profit_loss" in trade
    ]

    if len(valid_trades) == 0:
        return "No completed trades have been recorded yet."

    total = len(valid_trades)

    wins = sum(
        1 for trade in valid_trades
        if trade.get("profit_loss", 0) > 0
    )

    losses = total - wins

    total_profit = sum(
        trade.get("profit_loss", 0)
        for trade in valid_trades
    )

    win_rate = (wins / total) * 100

    return f"""
CORTEX LEARNING REPORT

Completed Trades: {total}
Wins: {wins}
Losses: {losses}
Win Rate: {win_rate:.2f}%
Total Profit/Loss: ${total_profit:.2f}
"""
def get_learning_context():

    memory = load_memory()

    if len(memory) == 0:
        return "No previous trade history available."

    valid_trades = [
        trade for trade in memory
        if "profit_loss" in trade
    ]

    if len(valid_trades) == 0:
        return "No completed trades available."

    wins = sum(
        1 for trade in valid_trades
        if trade["profit_loss"] > 0
    )

    total = len(valid_trades)

    win_rate = (wins / total) * 100

    profit = sum(
        trade["profit_loss"]
        for trade in valid_trades
    )

    return f"""
Previous Cortex Performance:

Trades: {total}
Win Rate: {win_rate:.2f}%
Total P/L: ${profit:.2f}

Use this history when evaluating new trades.
"""