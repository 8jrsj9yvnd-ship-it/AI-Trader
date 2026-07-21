import ollama

MODEL = "hermes3:latest"

SYSTEM_PROMPT = """
You are Cortex, an autonomous trading assistant.

You help monitor and analyze the trading system.

Your responsibilities:
- Explain market conditions
- Explain stock scans
- Explain trade decisions
- Report risk information
- Communicate clearly and concisely

Never claim a trade happened unless the trading system confirms it.
Always explain the reasoning behind decisions.
"""


def ask_cortex(message):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    return response["message"]["content"]