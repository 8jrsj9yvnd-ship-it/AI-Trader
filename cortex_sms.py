from twilio.rest import Client
from datetime import datetime
import schedule
import time
import os

from alpaca.trading.client import TradingClient
from dotenv import load_dotenv


load_dotenv()


# =========================
# TWILIO SETTINGS
# =========================

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

YOUR_PHONE = "+18057109779"


if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_PHONE:
    raise Exception(
        "Missing Twilio settings in .env file"
    )


sms = Client(
    TWILIO_SID,
    TWILIO_TOKEN
)


# =========================
# ALPACA CONNECTION
# =========================

alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)



def send_cortex_update():

    try:

        account = alpaca.get_account()

        equity = float(account.equity)
        cash = float(account.cash)

        positions = alpaca.get_all_positions()


        total_profit = sum(
            float(p.unrealized_pl)
            for p in positions
        )


        position_text = "None"

        if positions:

            position_text = "\n".join(
                [
                    f"{p.symbol}: {p.qty} shares | P/L ${float(p.unrealized_pl):,.2f}"
                    for p in positions
                ]
            )


        message = f"""
🤖 CORTEX UPDATE

Time:
{datetime.now().strftime("%I:%M %p")}

Account Value:
${equity:,.2f}

Cash:
${cash:,.2f}

Open Position P/L:
${total_profit:,.2f}

Positions:
{position_text}

Cortex is online and monitoring markets.
"""


        sms.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=YOUR_PHONE
        )


        print("Cortex update sent")


    except Exception as e:

        print(
            "SMS ERROR:",
            e
        )



# =========================
# UPDATE TIMES
# =========================

schedule.every().day.at("13:00").do(send_cortex_update)
schedule.every().day.at("16:00").do(send_cortex_update)
schedule.every().day.at("18:00").do(send_cortex_update)
schedule.every().day.at("20:00").do(send_cortex_update)
schedule.every().day.at("23:00").do(send_cortex_update)



if __name__ == "__main__":

    print("Cortex SMS system active")

    while True:

        schedule.run_pending()

        time.sleep(30)