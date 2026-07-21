import time
import subprocess
from datetime import datetime
from market_hours import market_open


RUN_INTERVAL = 900


print("AI Trader Loop Started")


while True:

    print("\n====================")
    print(datetime.now())
    print("====================")


    open_market, message = market_open()


    print(message)


    # Always manage existing trades
    print("\nChecking positions...")
    
    subprocess.run(
        [
            "python",
            "trade_manager.py"
        ]
    )


    # Only search for new trades when market is open
    if open_market:

        print("\nRunning market scanner...")

        subprocess.run(
            [
                "python",
                "autonomous_controller.py"
            ]
        )

    else:

        print("Market closed - skipping new trades")


    print("\nWaiting 15 minutes...")

    time.sleep(RUN_INTERVAL)