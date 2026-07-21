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


for order in orders:

    if str(order.status) in ["OrderStatus.NEW", "OrderStatus.ACCEPTED"]:

        print("Cancelling:", order.symbol, order.id)

        alpaca.cancel_order_by_id(
            order.id
        )


print("Done")