from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

load_dotenv()

alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

clock = alpaca.get_clock()

print("Market open:", clock.is_open)
print("Current time:", clock.timestamp)
print("Next open:", clock.next_open)
print("Next close:", clock.next_close)