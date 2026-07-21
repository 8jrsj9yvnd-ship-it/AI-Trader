from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os

load_dotenv()

client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

account = client.get_account()

print("STATUS:", account.status)
print("CASH:", account.cash)
print("EQUITY:", account.equity)
print("BUYING POWER:", account.buying_power)