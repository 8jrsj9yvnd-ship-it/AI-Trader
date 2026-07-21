from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
import os
import time
import subprocess


load_dotenv()


alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


print("Cortex is online.")
print("Waiting for market open...")


while True:

    clock = alpaca.get_clock()

    if clock.is_open:

        print("Market is open.")
        print("Starting Cortex trading system.")

        subprocess.run(
            ["python", "autonomous_controller.py"]
        )

        break


    else:

        print(
            "Market closed. Next open:",
            clock.next_open
        )

    time.sleep(60)