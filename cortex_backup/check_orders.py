from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


orders = alpaca.get_orders()


print("\n===== RECENT ORDERS =====")

for order in orders:

    print(
        order.symbol,
        order.side,
        "Qty:",
        order.qty,
        "Status:",
        order.status,
        "Filled:",
        order.filled_qty,
        "Fill Price:",
        order.filled_avg_price
    )