def score_stock(stock):

    score = 0

    # Trend
    if stock["price"] > stock["sma20"]:
        score += 30

    if stock["sma20"] > stock["sma50"]:
        score += 30

    # Momentum
    if 40 <= stock["rsi"] <= 70:
        score += 30

    # Bonus for stronger momentum
    if stock["rsi"] > 50:
        score += 10

    return score

