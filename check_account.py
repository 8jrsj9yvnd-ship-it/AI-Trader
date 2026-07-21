from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

print("OPEN POSITIONS:\n")

positions = client.get_all_positions()

if len(positions) == 0:
    print("No filled positions yet.")
else:
    for p in positions:
        print(
            p.symbol,
            "Shares:",
            p.qty,
            "Entry:",
            p.avg_entry_price
        )


print("\nRECENT ORDERS:\n")

orders = client.get_orders()

for o in orders[:10]:
    print(
        o.symbol,
        o.side,
        "Qty:",
        o.qty,
        "Status:",
        o.status,
        "Filled:",
        o.filled_qty,
        "Fill Price:",
        o.filled_avg_price
    )