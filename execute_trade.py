from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from dotenv import load_dotenv
import os

import risk_manager


# SAFETY SWITCH
# False = paper trading only
# True = live trading (do not enable until fully tested)
LIVE_TRADING = False


if LIVE_TRADING:
    print("⚠️ LIVE TRADING MODE ACTIVE")
else:
    print("🟢 PAPER TRADING MODE ACTIVE")


load_dotenv()


client = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=not LIVE_TRADING
)



def execute_trade(symbol, entry_price):

    """
    Cortex Trade Execution Engine

    Receives:
    - Stock symbol
    - Entry price

    Handles:
    - Account sizing
    - Risk calculation
    - Stop loss
    - Take profit
    - Alpaca order submission
    """


    account = client.get_account()

    account_value = float(account.equity)



    trade = risk_manager.calculate_trade(
        account_value,
        entry_price
    )



    if not trade["approved"]:

        return {
            "status": "REJECTED",
            "reason": trade.get(
                "reason",
                "Risk manager rejected trade"
            )
        }



    shares = trade["shares"]



    if shares < 1:

        return {
            "status": "REJECTED",
            "reason": "Position size too small"
        }



    order = MarketOrderRequest(

        symbol=symbol,

        qty=shares,

        side=OrderSide.BUY,

        time_in_force=TimeInForce.DAY,

        order_class=OrderClass.BRACKET,

        take_profit={
            "limit_price": trade["take_profit"]
        },

        stop_loss={
            "stop_price": trade["stop_loss"]
        }

    )



    submitted = client.submit_order(
        order
    )



    return {

        "status": "SUBMITTED",

        "symbol": symbol,

        "shares": shares,

        "entry": entry_price,

        "stop_loss": trade["stop_loss"],

        "take_profit": trade["take_profit"],

        "risk_amount": trade["risk_amount"],

        "order_id": str(submitted.id)

    }