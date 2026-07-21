from dotenv import load_dotenv
import os
from alpaca.trading.client import TradingClient

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

client = TradingClient(
    api_key,
    secret_key,
    paper=True
)


def get_trades():

    account = client.get_account()
    positions = client.get_all_positions()

    report = []

    report.append("CORTEX TRADES")
    report.append("================")
    report.append(f"Cash: ${float(account.cash):,.2f}")
    report.append("")

    if not positions:
        report.append("Cortex has not bought anything yet.")
        return "\n".join(report)

    for position in positions:
        report.append(f"{position.symbol}")
        report.append(f"Shares: {position.qty}")
        report.append(f"Buy Price: ${float(position.avg_entry_price):.2f}")
        report.append(f"Current Price: ${float(position.current_price):.2f}")
        report.append(
            f"Profit/Loss: ${float(position.unrealized_pl):.2f} "
            f"({float(position.unrealized_plpc)*100:.2f}%)"
        )
        report.append("")

    return "\n".join(report)