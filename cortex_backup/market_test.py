from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from dotenv import load_dotenv
import os

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

request = StockLatestQuoteRequest(
    symbol_or_symbols=["AAPL"]
)

quote = client.get_stock_latest_quote(request)

aapl = quote["AAPL"]

print("AAPL Bid:", aapl.bid_price)
print("AAPL Ask:", aapl.ask_price)