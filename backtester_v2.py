from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from dotenv import load_dotenv

import os
from datetime import datetime, timedelta


load_dotenv()


client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)


SYMBOL = "AAPL"

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

    return bars.df.reset_index()



def run_backtest(data):

    cash = STARTING_CASH

    shares = 0

    entry = 0

    trades = []



    for i in range(len(data)):

        price = float(data.iloc[i]["close"])



        if i >= 20:

            sma20 = data["close"].iloc[i-20:i].mean()



            if shares == 0 and price > sma20:


                shares = int(
                    (cash * POSITION_SIZE) / price
                )

                entry = price

                cash -= shares * price


                trades.append({
                    "type":"BUY",
                    "price":price
                })



            if shares > 0:


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



def analyze(trades, final):


    sells = [

        t["profit"]

        for t in trades

        if t["type"]=="SELL"

    ]


    wins = [

        x for x in sells

        if x > 0

    ]


    losses = [

        x for x in sells

        if x < 0

    ]



    print("\n===== PERFORMANCE =====")


    print(
        "Return:",
        round(
            ((final-STARTING_CASH)
            /STARTING_CASH)*100,
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
                len(wins)/len(sells)*100,
                2
            ),
            "%"
        )


        print(
            "Average Win:",
            round(
                max(wins)*100,2
            ),
            "%"
            if wins else "N/A"
        )


        print(
            "Average Loss:",
            round(
                min(losses)*100,2
            ),
            "%"
            if losses else "N/A"
        )


        print(
            "Best Trade:",
            round(max(sells)*100,2),
            "%"
        )


        print(
            "Worst Trade:",
            round(min(sells)*100,2),
            "%"
        )




print("""
===============================
     CORTEX BACKTESTER V2
===============================
""")


data = get_history(SYMBOL)


result, trades = run_backtest(data)



print(
    "Starting:",
    STARTING_CASH
)


print(
    "Ending:",
    round(result,2)
)


analyze(
    trades,
    result
)