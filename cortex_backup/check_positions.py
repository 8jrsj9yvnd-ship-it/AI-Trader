from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


positions = alpaca.get_all_positions()


print("\n===== OPEN POSITIONS =====")


if len(positions) == 0:
    print("No filled positions yet")

else:
    for p in positions:
        print(
            p.symbol,
            "Qty:",
            p.qty,
            "Entry:",
            p.avg_entry_price,
            "Current:",
            p.current_price,
            "P/L:",
            p.unrealized_pl
        )