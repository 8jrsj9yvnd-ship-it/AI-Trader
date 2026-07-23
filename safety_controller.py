from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from dotenv import load_dotenv
import config
import os

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

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


    if len(positions) >= config.MAX_OPEN_POSITIONS:
        return False, "Maximum positions reached"


    # Bounded by MAX_OPEN_POSITIONS (not a separate hardcoded cap) so this
    # can never throttle entries below the position count that was actually
    # walk-forward validated -- a pending order becomes a position once
    # filled, so the ceiling that matters is the same one either way.
    if len(open_orders) >= config.MAX_OPEN_POSITIONS:
        return False, "Too many open orders"


    return True, "Trade approved"