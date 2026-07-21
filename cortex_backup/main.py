from dotenv import load_dotenv
import os
from alpaca.trading.client import TradingClient
import subprocess
import threading
import time
import sys

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

client = TradingClient(
    api_key,
    secret_key,
    paper=True
)

account = client.get_account()

print("Connected!")
print("Account Status:", account.status)
print("Cash:", account.cash)
print("Buying Power:", account.buying_power)


python_executable = sys.executable


def start_discord():
    subprocess.Popen(
        [python_executable, "discord_bot.py"],
        cwd=os.getcwd()
    )


discord_thread = threading.Thread(target=start_discord)
discord_thread.start()

time.sleep(2)

print("Starting Cortex Trader...")

subprocess.run(
    [python_executable, "autonomous_controller.py"],
    cwd=os.getcwd()
)