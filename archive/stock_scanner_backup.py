from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
import os
from datetime import datetime, timedelta

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

stocks = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMD",
    "AMZN",
    "META",
    "GOOGL",
    "GOOG",
    "AVGO",
    "NFLX",
    "CRM",
    "ORCL",
    "ADBE",
    "INTC",
    "QCOM",
    "MU",
    "TXN",
    "AMAT",
    "LRCX",
    "PANW",
    "CRWD",
    "NOW",
    "UBER",
    "SHOP",
    "COST",
    "WMT",
    "JPM",
    "BAC",
    "GS",
    "MS",
    "V",
    "MA",
    "AXP",
    "LLY",
    "UNH",
    "JNJ",
    "MRK",
    "PFE",
    "XOM",
    "CVX",
    "COP",
    "CAT",
    "DE",
    "BA",
    "GE",
    "HON",
    "DIS",
    "CMCSA",
    "T",
    "VZ"
]


def analyze_stock(symbol):

    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=100),
        end=datetime.now()
    )

    bars = client.get_stock_bars(request)

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

    latest = data.iloc[-1]

    return {
        "symbol": symbol,
        "price": round(latest["close"], 2),
        "sma20": round(latest["SMA20"], 2),
        "sma50": round(latest["SMA50"], 2),
        "rsi": round(latest["RSI"], 2)
    }


if __name__ == "__main__":

    print("\n===== MARKET SCAN =====\n")

    for stock in stocks:
        try:
            result = analyze_stock(stock)
            print(result)

        except Exception as e:
            print(stock, "ERROR:", e)