from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
from indicators import add_indicators
import os
from datetime import datetime, timedelta

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

symbol = "AAPL"

request = StockBarsRequest(
    symbol_or_symbols=[symbol],
    timeframe=TimeFrame.Day,
    start=datetime.now() - timedelta(days=100),
    end=datetime.now()
)

bars = client.get_stock_bars(request)

data = bars.df

# Remove symbol level from dataframe
data = data.reset_index()

# Add indicators
analysis = add_indicators(data)

latest = analysis.iloc[-1]

print("\n----- MARKET REPORT -----")
print("Symbol:", symbol)
print("Price:", round(latest["close"], 2))
print("20 Day Average:", round(latest["SMA20"], 2))
print("50 Day Average:", round(latest["SMA50"], 2))
print("RSI:", round(latest["RSI"], 2))

if latest["SMA20"] > latest["SMA50"]:
    print("Trend: Bullish")
else:
    print("Trend: Bearish")

print("------------------------")