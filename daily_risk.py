from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


MAX_DAILY_LOSS = 500


def check_daily_loss():

    account = alpaca.get_account()


    equity = float(account.equity)

    last_equity = float(account.last_equity)


    loss = max(0, last_equity - equity)


    print("Daily Loss:", round(loss, 2))


    if loss >= MAX_DAILY_LOSS:

        return False, "Daily loss limit reached"


    return True, "Daily risk acceptable"