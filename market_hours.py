from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
from datetime import time as dtime
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


PRE_MARKET_START = dtime(4, 0)
REGULAR_START = dtime(9, 30)
REGULAR_END = dtime(16, 0)
AFTER_HOURS_END = dtime(20, 0)


def get_session():
    """
    One of "REGULAR", "PRE_MARKET", "AFTER_HOURS", "CLOSED".

    clock.timestamp comes back Eastern-time aware from Alpaca, so the
    extended-hours windows are compared against it directly.
    """

    clock = alpaca.get_clock()

    if clock.is_open:
        return "REGULAR"

    now = clock.timestamp
    t = now.time()

    if now.weekday() >= 5:
        return "CLOSED"

    if PRE_MARKET_START <= t < REGULAR_START:
        return "PRE_MARKET"

    if REGULAR_END <= t < AFTER_HOURS_END:
        return "AFTER_HOURS"

    return "CLOSED"