import schedule
import time
import datetime
import subprocess


def trading_cycle():

    now = datetime.datetime.now()

    print("\n====================")
    print("BOT CHECK:", now)
    print("====================")

    # Run your AI trader
    subprocess.run(
        ["python", "autonomous_controller.py"]
    )


def market_check():

    now = datetime.datetime.now()

    # Monday-Friday only
    if now.weekday() < 5:

        # Market hours (simple version)
        if 6 <= now.hour <= 13:

            trading_cycle()

        else:
            print("Outside market hours")

    else:
        print("Market closed - weekend")


schedule.every(15).minutes.do(market_check)


print("AI Trader Running...")


while True:

    schedule.run_pending()

    time.sleep(30)