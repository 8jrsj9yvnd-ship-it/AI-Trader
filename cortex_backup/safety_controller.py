from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from dotenv import load_dotenv
import os

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

MAX_POSITIONS = 3
MAX_OPEN_ORDERS = 3


def check_safety(symbol):

    positions = client.get_all_positions()

    for position in positions:
        if position.symbol == symbol:
            return False, "Already own this stock"


    request = GetOrdersRequest(
        status="open"
    )

    open_orders = client.get_orders(request)


    for order in open_orders:
        if order.symbol == symbol:
            return False, "Already have an open order for this stock"


    if len(positions) >= MAX_POSITIONS:
        return False, "Maximum positions reached"


    if len(open_orders) >= MAX_OPEN_ORDERS:
        return False, "Too many open orders"


    return True, "Trade approved"