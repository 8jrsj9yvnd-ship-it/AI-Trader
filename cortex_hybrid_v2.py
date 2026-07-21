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
MIN_HOLD_DAYS = 3



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


    if 50 <= row["RSI"] <= 70:
        score += 20


    return score



def run_cortex(history):

    cash = STARTING_CASH

    positions = {}


    trades = 0
    buys = 0
    sells = 0

    wins = 0
    losses = 0

    winning_profit = 0
    losing_loss = 0


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


        # SELL CHECK

        for symbol in list(positions):

            row = history[symbol].iloc[day]

            pos = positions[symbol]


            days_held = day - pos["day"]


            score = cortex_score(row)


            if days_held >= MIN_HOLD_DAYS and score < 60:

                price = float(row["close"])


                profit = (
                    price - pos["entry"]
                ) * pos["shares"]


                if profit > 0:
                    wins += 1
                    winning_profit += profit

                else:
                    losses += 1
                    losing_loss += profit


                print(
                    "SELL",
                    symbol,
                    price,
                    "Weak Momentum"
                )


                cash += (
                    pos["shares"] * price
                )


                del positions[symbol]


                trades += 1
                sells += 1
        # BUY CHECK

        for symbol,score,price in top:


            if symbol not in positions and score >= 80:


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


                    print(
                        "BUY",
                        symbol,
                        "Score:",
                        score,
                        "Price:",
                        price,
                        "Shares:",
                        shares
                    )


                    positions[symbol] = {

                        "shares": shares,

                        "entry": price,

                        "high": price,

                        "day": day

                    }


                    cash -= shares * price


                    trades += 1
                    buys += 1



        # WINNER / LOSER MANAGEMENT

        for symbol in list(positions):

            price = float(
                history[symbol]
                .iloc[day]["close"]
            )


            pos = positions[symbol]


            if price > pos["high"]:
                pos["high"] = price



            gain = (
                price - pos["entry"]
            ) / pos["entry"]



            drop = (
                price - pos["high"]
            ) / pos["high"]



            if gain >= .30 and drop <= -.10 or gain <= -.05:


                profit = (
                    price - pos["entry"]
                ) * pos["shares"]



                if profit > 0:
                    wins += 1
                    winning_profit += profit

                else:
                    losses += 1
                    losing_loss += profit



                reason = (
                    "Trailing Stop"
                    if gain >= .30
                    else
                    "Stop Loss"
                )


                print(
                    "SELL",
                    symbol,
                    price,
                    reason
                )


                cash += (
                    pos["shares"] * price
                )


                del positions[symbol]


                trades += 1
                sells += 1



    total = cash


    for symbol,pos in positions.items():

        price = float(
            history[symbol]
            .iloc[-1]["close"]
        )


        total += (
            pos["shares"] * price
        )



    print()
    print("==============================")
    print("TRADE SUMMARY")
    print("==============================")

    print("Total Trades:", trades)
    print("Buys:", buys)
    print("Sells:", sells)
    print("Open Positions:", len(positions))

    print("Wins:", wins)
    print("Losses:", losses)


    if wins + losses > 0:

        print(
            "Win Rate:",
            round((wins/(wins+losses))*100,2),
            "%"
        )


    print(
        "Average Win:",
        round(winning_profit/max(wins,1),2)
    )


    print(
        "Average Loss:",
        round(losing_loss/max(losses,1),2)
    )


    return total





print("""
=====================================
       CORTEX HYBRID V2 TEST
=====================================
""")


history = {}


for stock in STOCKS:

    print("Loading", stock)

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
    round(result - STARTING_CASH,2)
)