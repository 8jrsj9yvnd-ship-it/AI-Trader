import json
from risk_manager import calculate_position_size

ai_response = """
{
  "signal": "BUY",
  "confidence": 75,
  "reason": "Bullish trend with strong momentum",
  "risk": "MEDIUM"
}
"""

trade = json.loads(ai_response)

account_balance = 100000
entry_price = 327.50

if trade["signal"] == "BUY" and trade["confidence"] >= 70:

    position = calculate_position_size(
        account_balance,
        entry_price
    )

    print("TRADE APPROVED")
    print(position)

else:
    print("TRADE REJECTED")