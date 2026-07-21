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


STOCKS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMD",
    "AMZN",
    "META",
    "PANW"
]


STARTING_CASH = 10000


def get_history(symbol):

    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=365),
        end=datetime.now()
    )

    bars = client.get_stock_bars(request)

    data = bars.df.reset_index()

    data["SMA20"] = SMAIndicator(
        data["close"], window=20
    ).sma_indicator()

    data["SMA50"] = SMAIndicator(
        data["close"], window=50
    ).sma_indicator()

    data["RSI"] = RSIIndicator(
        data["close"], window=14
    ).rsi()

    return data



def cortex_score(row):

    score = 0

    if row["close"] > row["SMA20"]:
        score += 25

    if row["SMA20"] > row["SMA50"]:
        score += 25

    if row["close"] > row["SMA50"]:
        score += 20

    if 45 <= row["RSI"] <= 75:
        score += 20

    return score



def run_cortex(data):

    cash = STARTING_CASH
    shares = 0
    entry = 0
    highest = 0


    for i in range(len(data)):

        row = data.iloc[i]

        price = float(row["close"])

        score = cortex_score(row)


        if shares == 0:

            if score >= 70:

                # stronger signals get more capital
                if score >= 90:
                    allocation = .75
                elif score >= 80:
                    allocation = .60
                else:
                    allocation = .40


                shares = int(
                    (cash * allocation) / price
                )

                entry = price
                highest = price

                cash -= shares * price


        else:

            if price > highest:
                highest = price


            gain = (
                price-entry
            ) / entry


            drop = (
                price-highest
            ) / highest


            # protect winners
            if gain >= .15 and drop <= -.05:

                cash += shares * price
                shares = 0


            # stop loss
            elif gain <= -.08:

                cash += shares * price
                shares = 0



    return cash + (
        shares *
        float(data.iloc[-1]["close"])
    )



def buy_hold(data):

    start = float(data.iloc[0]["close"])
    end = float(data.iloc[-1]["close"])

    return STARTING_CASH * (end/start)



print("""
=====================================
        CORTEX BACKTESTER
=====================================
""")


results = []


for stock in STOCKS:

    try:

        data = get_history(stock)

        cortex = run_cortex(data)

        hold = buy_hold(data)

        results.append(cortex)


        print("\n----------------")
        print(stock)
        print("----------------")

        print("Cortex:", round(cortex,2))
        print("Buy Hold:", round(hold,2))
        print("Difference:", round(cortex-hold,2))


    except Exception as e:

        print(stock, e)



print("""
==============================
SUMMARY
==============================
""")


print(
    "Average Cortex:",
    round(sum(results)/len(results),2)
)