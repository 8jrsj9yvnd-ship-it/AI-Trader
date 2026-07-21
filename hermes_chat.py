import ollama


print("Hermes Trading Assistant")
print("Type 'exit' to quit\n")


while True:

    message = input("You: ")

    if message.lower() == "exit":
        break


    response = ollama.chat(
        model="hermes3:latest",
        messages=[
            {
                "role": "system",
                "content": """
You are Hermes, the AI assistant inside a local algorithmic trading system.

Current progress:
- Python trading bot created
- Alpaca paper trading connected
- Market scanner working
- Technical indicators working
- Stock ranking working
- Risk manager working
- Safety controller working
- Automated order submission working
- Currently testing and improving the system

Explain your reasoning clearly.
Do not pretend trades are profitable unless proven by data.
"""
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )


    print("\nHermes:")
    print(response["message"]["content"])
    print()