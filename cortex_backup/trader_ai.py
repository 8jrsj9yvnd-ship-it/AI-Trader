from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import ollama
import os
from datetime import datetime, timedelta
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

market_client = StockHistoricalDataClient(
    api_key,
    secret_key
)


def get_market_data(symbol):

    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=100),
        end=datetime.now()
    )

    bars = market_client.get_stock_bars(request)

    data = bars.df.reset_index()

    data["SMA20"] = SMAIndicator(
        data["close"],
        window=20
    ).sma_indicator()

    data["SMA50"] = SMAIndicator(
        data["close"],
        window=50
    ).sma_indicator()

    data["RSI"] = RSIIndicator(
        data["close"],
        window=14
    ).rsi()

    return data.iloc[-1]


def ask_ai(report):

    response = ollama.chat(
        model="hermes3:latest",
        format="json",
        messages=[
            {
                "role": "system",
                "content": """
You are a trading analysis AI.

Analyze the market data.

Return ONLY valid JSON.

Use this exact format:

{
  "signal": "BUY, HOLD, or SELL",
  "confidence": 0-100,
  "reason": "short explanation",
  "risk": "LOW, MEDIUM, or HIGH"
}

Do not include any other text.
"""
            },
            {
                "role": "user",
                "content": report
            }
        ]
    )

    return response["message"]["content"]


symbol = "AAPL"

data = get_market_data(symbol)

report = f"""
Stock: {symbol}

Price: {data['close']:.2f}
SMA20: {data['SMA20']:.2f}
SMA50: {data['SMA50']:.2f}
RSI: {data['RSI']:.2f}
"""

print("MARKET DATA")
print(report)

print("\nAI ANALYSIS")
print(ask_ai(report))