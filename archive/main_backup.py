from dotenv import load_dotenv
import os
from alpaca.trading.client import TradingClient

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

client = TradingClient(
    api_key,
    secret_key,
    paper=True
)

account = client.get_account()

print("Connected!")
print("Account Status:", account.status)
print("Cash:", account.cash)
print("Buying Power:", account.buying_power)