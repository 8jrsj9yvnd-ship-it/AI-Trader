from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from dotenv import load_dotenv

from datetime import datetime, timedelta

import os


load_dotenv()


data_client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)



def market_is_good():

    try:

        request = StockBarsRequest(
            symbol_or_symbols=["SPY"],
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=90),
            end=datetime.now(),
            feed=DataFeed.IEX
        )


        response = data_client.get_stock_bars(request)


        bars = response.df


        if bars.empty:

            return False, "No SPY data available"



        spy = bars.xs(
            "SPY",
            level="symbol"
        )


        close = spy["close"].values


        if len(close) < 50:

            return False, "Not enough SPY data"



        current_price = close[-1]


        sma50 = sum(close[-50:]) / 50



        print("\nSPY Price:", round(current_price, 2))

        print(
            "SPY 50 Day Average:",
            round(sma50, 2)
        )



        if current_price > sma50:

            return True, "Market trend is positive"



        else:

            return False, "Market trend is weak"



    except Exception as e:

        return False, f"Market filter error: {e}"