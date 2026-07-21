import ollama
import json
import os


FILE = "trades.json"


def load_trades():

    if not os.path.exists(FILE):
        return []

    with open(FILE, "r") as f:
        return json.load(f)



def ask_hermes(trades):

    prompt = f"""
You are reviewing an automated trading system.

Analyze these completed trades:

{json.dumps(trades, indent=2)}

Return ONLY JSON:

{{
"performance_summary": "summary",
"strengths": [
"strength 1"
],
"weaknesses": [
"weakness 1"
],
"recommended_changes": [
"change 1"
]
}}
"""

    response = ollama.chat(
        model="hermes3:latest",
        format="json",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )


    return json.loads(
        response["message"]["content"]
    )



trades = load_trades()


if len(trades) == 0:

    print("No trades to review")

else:

    review = ask_hermes(trades)

    print("\n===== HERMES REVIEW =====")

    print(json.dumps(
        review,
        indent=2
    ))