from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import config
import os


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


def check_daily_loss():

    account = alpaca.get_account()


    equity = float(account.equity)

    last_equity = float(account.last_equity)


    # Alpaca's paper API has been observed returning last_equity=0 (instead
    # of the prior trading day's close) around session boundaries. A real
    # previous-day equity of $0 is impossible for an account with trading
    # history -- treat that reading as unavailable rather than computing a
    # $0 daily-loss budget that blocks every single trade for the rest of
    # the day over a data glitch, not a real loss.
    if last_equity <= 0:

        print("Daily Loss: last_equity unavailable (0) -- skipping check this cycle")

        return True, "Daily risk check skipped (no valid prior-day equity reference)"


    loss = max(0, last_equity - equity)

    max_daily_loss = last_equity * config.MAX_DAILY_LOSS


    print("Daily Loss:", round(loss, 2), "/ Limit:", round(max_daily_loss, 2))


    if loss >= max_daily_loss:

        return False, "Daily loss limit reached"


    return True, "Daily risk acceptable"