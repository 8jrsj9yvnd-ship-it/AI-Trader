from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from dotenv import load_dotenv

from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

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
    "AVGO",
    "NFLX",
    "PANW",
    "CRWD",
    "UBER",
    "SHOP",
    "COST",
    "JPM",
    "GS",
    "LLY",
    "XOM",
    "CAT"
]


def analyze_stock(symbol):

    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=150),
        end=datetime.now()
    )


    bars = client.get_stock_bars(request)

    data = bars.df.reset_index()


    if len(data) < 60:
        raise Exception("Not enough data")


    close = data["close"]
    volume = data["volume"]


    data["SMA20"] = SMAIndicator(
        close,
        window=20
    ).sma_indicator()


    data["SMA50"] = SMAIndicator(
        close,
        window=50
    ).sma_indicator()


    data["RSI"] = RSIIndicator(
        close,
        window=14
    ).rsi()


    data["ATR"] = AverageTrueRange(
        high=data["high"],
        low=data["low"],
        close=close,
        window=14
    ).average_true_range()



    latest = data.iloc[-1]


    price = float(latest["close"])
    sma20 = float(latest["SMA20"])
    sma50 = float(latest["SMA50"])
    rsi = float(latest["RSI"])
    atr = float(latest["ATR"])



    avg_volume = float(
        volume.tail(20).mean()
    )


    volume_strength = float(
        latest["volume"] / avg_volume
    )


    day_change = (
        (price - float(data.iloc[-2]["close"]))
        /
        float(data.iloc[-2]["close"])
        *
        100
    )


    five_day_change = (
        (price - float(data.iloc[-6]["close"]))
        /
        float(data.iloc[-6]["close"])
        *
        100
    )


    twenty_day_change = (
        (price - float(data.iloc[-21]["close"]))
        /
        float(data.iloc[-21]["close"])
        *
        100
    )



    score = 0
    reasons = []



    # TREND

    if price > sma20:
        score += 20
        reasons.append("Above 20 day trend")


    if sma20 > sma50:
        score += 20
        reasons.append("Strong upward trend")



    # MOMENTUM

    if 50 <= rsi <= 65:
        score += 20
        reasons.append("Healthy momentum")


    elif rsi > 70:
        score -= 10
        reasons.append("Overbought risk")



    # VOLUME

    if volume_strength > 1.2:
        score += 15
        reasons.append("Volume confirmation")


    elif volume_strength < .8:
        score -= 5
        reasons.append("Weak volume")



    # PERFORMANCE

    if five_day_change > 3:
        score += 10


    if twenty_day_change > 10:
        score += 15
        reasons.append("Strong recent performance")



    # RISK CONTROL

    volatility = atr / price


    if volatility > .05:
        score -= 10
        reasons.append("High volatility")



    score = max(
        0,
        min(score,100)
    )



    if score >= 75:
        bias = "BUY WATCH"

    elif score >= 50:
        bias = "NEUTRAL"

    else:
        bias = "AVOID"



    return {

        "symbol": symbol,

        "price": round(price,2),

        "sma20": round(sma20,2),

        "sma50": round(sma50,2),

        "rsi": round(rsi,2),

        "atr": round(atr,2),

        "volume_strength": round(volume_strength,2),

        "day_change": round(day_change,2),

        "five_day_change": round(five_day_change,2),

        "twenty_day_change": round(twenty_day_change,2),

        "score": score,

        "bias": bias,

        "reason": ", ".join(reasons)

    }



if __name__ == "__main__":


    print("\n==============================")
    print("       CORTEX MARKET SCAN")
    print("==============================")



    results = []


    for stock in stocks:

        try:

            results.append(
                analyze_stock(stock)
            )

        except Exception as e:

            print(
                stock,
                e
            )



    results.sort(
        key=lambda x:x["score"],
        reverse=True
    )



    for stock in results:


        print(f"""

------------------------------
{stock['symbol']}
------------------------------

Price: ${stock['price']}

CORTEX SCORE: {stock['score']}/100
BIAS: {stock['bias']}

RSI: {stock['rsi']}
Volume: {stock['volume_strength']}x

1 Day: {stock['day_change']}%
5 Day: {stock['five_day_change']}%
20 Day: {stock['twenty_day_change']}%

Reason:
{stock['reason']}

""")

