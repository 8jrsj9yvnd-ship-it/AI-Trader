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
COOLDOWN_DAYS = 10



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

    cooldown = {}

    trades = []


    days = len(
        list(history.values())[0]
    )


    for day in range(days):


        # reduce cooldown counters

        for stock in list(cooldown):

            cooldown[stock] -= 1

            if cooldown[stock] <= 0:
                del cooldown[stock]



        rankings = []


        for symbol,data in history.items():

            row = data.iloc[day]

            rankings.append(
                (
                    symbol,
                    cortex_score(row),
                    float(row["close"])
                )
            )


        rankings.sort(
            key=lambda x:x[1],
            reverse=True
        )


        top = rankings[:MAX_POSITIONS]



        # SELL LOGIC

        for symbol in list(positions):

            row = history[symbol].iloc[day]

            score = cortex_score(row)

            price = float(row["close"])

            pos = positions[symbol]


            if price > pos["high"]:
                pos["high"] = price


            gain = (
                price-pos["entry"]
            ) / pos["entry"]


            drop = (
                price-pos["high"]
            ) / pos["high"]


            sell = False
            reason = ""


            # big winners breathe

            if gain >= .50 and drop <= -.20:

                sell = True
                reason = "50% trail"


            elif gain >= .20 and drop <= -.15:

                sell = True
                reason = "20% trail"


            # cut losers

            elif gain <= -.08:

                sell = True
                reason = "Stop loss"


            # momentum died

            elif score < 60:

                sell = True
                reason = "Momentum lost"



            if sell:

                pnl = gain * 100


                trades.append(
                    f"SELL {symbol} @ {price:.2f} | {pnl:.2f}% | {reason}"
                )


                cash += pos["shares"] * price

                del positions[symbol]

                cooldown[symbol] = COOLDOWN_DAYS



        # BUY LOGIC

        for symbol,score,price in top:


            if (
                symbol not in positions
                and symbol not in cooldown
                and score >= 70
            ):


                if score >= 90:
                    allocation = .35

                elif score >= 80:
                    allocation = .30

                else:
                    allocation = .20



                shares = int(
                    (cash * allocation) / price
                )


                if shares > 0:


                    positions[symbol] = {
                        "shares": shares,
                        "entry": price,
                        "high": price
                    }


                    trades.append(
                        f"BUY {symbol} @ {price:.2f} | Score {score}"
                    )


                    cash -= shares * price



    total = cash


    for symbol,pos in positions.items():

        price = float(
            history[symbol]
            .iloc[-1]["close"]
        )

        total += pos["shares"] * price



    return total,trades



print("""
=====================================
       CORTEX TREND RIDER
=====================================
""")


history = {}


for stock in STOCKS:

    history[stock] = get_history(stock)



result,trades = run_cortex(history)



print()
print("==============================")
print("RESULT")
print("==============================")


print(
    "Cortex:",
    round(result,2)
)


print(
    "Profit:",
    round(result-STARTING_CASH,2)
)


print()
print("==============================")
print("TRADES")
print("==============================")


for trade in trades:
    print(trade)