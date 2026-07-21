import ollama

def analyze_market(report):

    response = ollama.chat(
        model="hermes3:latest",
        messages=[
            {
                "role": "system",
                "content": """
You are a market analysis AI.
Analyze stock data logically.
Do not guarantee profits.
Return:
1. Signal (BUY/HOLD/SELL)
2. Confidence percentage
3. Reasoning
4. Risks
"""
            },
            {
                "role": "user",
                "content": report
            }
        ]
    )

    return response["message"]["content"]


market_report = """
Stock: AAPL
Price: 327.50
20 Day Average: 301.93
50 Day Average: 300.53
RSI: 68.85
Trend: Bullish
"""

analysis = analyze_market(market_report)

print(analysis)