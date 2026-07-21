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


# Stocks Cortex will test

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

POSITION_SIZE = 0.25



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




def cortex_signal(row):


    score = 0


    price = row["close"]

    sma20 = row["SMA20"]

    sma50 = row["SMA50"]

    rsi = row["RSI"]



    if price > sma20:
        score += 30


    if sma20 > sma50:
        score += 30


    if 45 <= rsi <= 65:
        score += 30


    if score >= 70:
        return True


    return False




def backtest(symbol, data):


    cash = STARTING_CASH

    shares = 0

    entry = 0

    trades = []



    for i in range(len(data)):


        row = data.iloc[i]


        price = float(row["close"])



        if shares == 0:


            if cortex_signal(row):


                shares = int(
                    (cash * POSITION_SIZE)
                    /
                    price
                )


                entry = price


                cash -= shares * price


                trades.append({

                    "type":"BUY",

                    "price":price

                })




        else:


            change = (
                price-entry
            ) / entry



            if change >= .10 or change <= -.05:


                cash += shares * price


                trades.append({

                    "type":"SELL",

                    "price":price,

                    "profit":change

                })


                shares = 0




    final = cash + (
        shares *
        float(data.iloc[-1]["close"])
    )


    return final, trades




def report(symbol, final, trades):


    sells = [

        t["profit"]

        for t in trades

        if t["type"]=="SELL"

    ]


    wins = [

        x for x in sells

        if x > 0

    ]


    print("\n======================")

    print(symbol)

    print("======================")


    print(
        "Ending:",
        round(final,2)
    )


    print(
        "Return:",
        round(
            ((final-STARTING_CASH)
            /
            STARTING_CASH)
            *100,
            2
        ),
        "%"
    )


    print(
        "Trades:",
        len(sells)
    )


    if sells:

        print(
            "Win Rate:",
            round(
                len(wins)
                /
                len(sells)
                *100,
                2
            ),
            "%"
        )





print("""
====================================
       CORTEX BACKTESTER V3
====================================
""")


for stock in STOCKS:


    try:

        history = get_history(stock)


        result, trades = backtest(
            stock,
            history
        )


        report(
            stock,
            result,
            trades
        )


    except Exception as e:

        print(
            stock,
            "ERROR",
            e
        )