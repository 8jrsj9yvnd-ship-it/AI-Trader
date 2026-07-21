import ollama

response = ollama.chat(
    model="hermes3:latest",
    messages=[
        {
            "role": "user",
            "content": "You are a financial AI assistant. Explain what a moving average is in one sentence."
        }
    ]
)

print(response["message"]["content"])