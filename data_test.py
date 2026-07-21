from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
from dotenv import load_dotenv
import os

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

request = StockLatestTradeRequest(
    symbol_or_symbols=["AAPL"]
)

response = client.get_stock_latest_trade(request)

print(response)