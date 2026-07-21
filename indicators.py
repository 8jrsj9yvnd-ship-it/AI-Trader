import pandas as pd
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

def add_indicators(data):

    data = data.copy()

    data["SMA20"] = SMAIndicator(
        close=data["close"],
        window=20
    ).sma_indicator()

    data["SMA50"] = SMAIndicator(
        close=data["close"],
        window=50
    ).sma_indicator()

    data["RSI"] = RSIIndicator(
        close=data["close"],
        window=14
    ).rsi()

    return data