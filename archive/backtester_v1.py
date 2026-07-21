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

POSITION_SIZE = 0.25   # 25% of account


def get_history(symbol):

    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=365),
        end=datetime.now()
    )

    bars = client.get_stock_bars(request)

    data = bars.df.reset_index()

    return data



def run_backtest(data):

    cash = STARTING_CASH

    shares = 0

    entry_price = 0

    trades = []


    for i in range(len(data)):

        price = float(
            data.iloc[i]["close"]
        )


        # BUY RULE
        #
        # simple first strategy:
        # buy after price rises above 20 day average


        if i >= 20:


            sma20 = data["close"].iloc[i-20:i].mean()


            if shares == 0 and price > sma20:


                investment = cash * POSITION_SIZE

                shares = int(
                    investment / price
                )

                entry_price = price

                cash -= shares * price


                trades.append({

                    "type":"BUY",
                    "price":price

                })


            # SELL RULE

            if shares > 0:


                profit = (
                    price-entry_price
                ) / entry_price


                if profit >= .10 or profit <= -.05:


                    cash += shares * price


                    trades.append({

                        "type":"SELL",
                        "price":price,
                        "profit":profit

                    })


                    shares = 0



    final_value = cash + (
        shares *
        float(data.iloc[-1]["close"])
    )


    return final_value, trades




print("""
===============================
     CORTEX BACKTESTER
===============================
""")


history = get_history(SYMBOL)


result, trades = run_backtest(history)



print("Symbol:", SYMBOL)

print("Starting Money:")
print("$", STARTING_CASH)


print("\nEnding Money:")
print("$", round(result,2))


profit = result - STARTING_CASH


print("\nProfit:")
print("$", round(profit,2))


print("\nTrades:")
print(len(trades))


for trade in trades[-10:]:

    print(trade)