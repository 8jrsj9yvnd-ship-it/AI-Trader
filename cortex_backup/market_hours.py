from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


def market_open():

    clock = alpaca.get_clock()

    if clock.is_open:
        return True, "Market is open"

    else:
        return False, f"Market closed. Opens at {clock.next_open}"