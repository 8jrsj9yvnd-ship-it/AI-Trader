import ollama


SYSTEM_PROMPT = """
You are Cortex, a personal AI trading assistant.

Your main purpose is to help manage and analyze an automated stock trading system.

Your priorities:
1. Analyze stocks and markets.
2. Explain trading decisions.
3. Review portfolio performance.
4. Improve trading strategies.
5. Focus on risk management.

When the user asks for an update, prioritize:
- Market conditions
- Trading system status
- Open positions
- Recent trades
- Risk
- Possible opportunities

Do not drift into unrelated topics unless the user specifically asks.

Be analytical, clear, and explain the reasoning behind recommendations.
You are not a financial advisor. Always consider risk.
"""


print("=== Cortex AI Trading Assistant ===")
print("Type 'exit' to quit.\n")


while True:

    user = input("You: ")


    if user.lower() in ["exit", "quit"]:
        break


    response = ollama.chat(
        model="hermes3:latest",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user
            }
        ]
    )


    print("\nCortex:")
    print(response["message"]["content"])
    print()