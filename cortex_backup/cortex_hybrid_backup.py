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
MAX_POSITIONS = 3



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


    return data



def cortex_score(row):

    score = 0


    if row["close"] > row["SMA20"]:
        score += 25


    if row["SMA20"] > row["SMA50"]:
        score += 30


    if row["close"] > row["SMA50"]:
        score += 25


    if 45 <= row["RSI"] <= 75:
        score += 20


    return score



def run_cortex(history):

    cash = STARTING_CASH

    positions = {}


    days = len(
        list(history.values())[0]
    )


    for day in range(days):


        rankings = []


        for symbol,data in history.items():

            row = data.iloc[day]

            score = cortex_score(row)

            rankings.append(
                (
                    symbol,
                    score,
                    float(row["close"])
                )
            )


        rankings.sort(
            key=lambda x:x[1],
            reverse=True
        )


        top = rankings[:MAX_POSITIONS]


        # Sell stocks that lose momentum

        for symbol in list(positions):

            current_score = 0

            row = history[symbol].iloc[day]

            current_score = cortex_score(row)


            if current_score < 60:

                price = float(row["close"])

                cash += (
                    positions[symbol]["shares"]
                    *
                    price
                )

                del positions[symbol]



        # Buy strongest opportunities

        for symbol,score,price in top:


            if symbol not in positions and score >= 70:


                if score >= 90:
                    allocation = .35

                elif score >= 80:
                    allocation = .30

                else:
                    allocation = .20


                amount = cash * allocation


                shares = int(
                    amount / price
                )


                if shares > 0:

                    positions[symbol] = {
                        "shares": shares,
                        "entry": price,
                        "high": price
                    }


                    cash -= shares * price



        # Manage winners

        for symbol in list(positions):

            price = float(
                history[symbol]
                .iloc[day]["close"]
            )


            pos = positions[symbol]


            if price > pos["high"]:
                pos["high"] = price


            gain = (
                price-pos["entry"]
            ) / pos["entry"]


            drop = (
                price-pos["high"]
            ) / pos["high"]


            if gain >= .30 and drop <= -.10:

                cash += (
                    pos["shares"]
                    *
                    price
                )

                del positions[symbol]


            elif gain <= -.10:

                cash += (
                    pos["shares"]
                    *
                    price
                )

                del positions[symbol]



    total = cash


    for symbol,pos in positions.items():

        price = float(
            history[symbol]
            .iloc[-1]["close"]
        )

        total += (
            pos["shares"]
            *
            price
        )


    return total



print("""
=====================================
       CORTEX HYBRID TEST
=====================================
""")


history = {}


for stock in STOCKS:

    history[stock] = get_history(stock)



result = run_cortex(history)



print()
print("==============================")
print("FINAL VALUE")
print("==============================")

print(
    "Cortex:",
    round(result,2)
)

print(
    "Profit:",
    round(result-STARTING_CASH,2)
)