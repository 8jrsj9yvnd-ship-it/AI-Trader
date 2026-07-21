def score_stock(stock):

    score = 50


    price = stock["price"]
    sma20 = stock["sma20"]
    sma50 = stock["sma50"]
    rsi = stock["rsi"]


    # Trend strength

    if price > sma20:
        score += 10

    else:
        score -= 10


    if sma20 > sma50:
        score += 15

    else:
        score -= 15


    if price > sma50:
        score += 10



    # Momentum

    if 50 <= rsi <= 65:
        score += 15

    elif 65 < rsi <= 75:
        score += 5

    elif rsi > 80:
        score -= 15

    elif rsi < 40:
        score -= 10



    # Strong acceleration

    if price > sma20 * 1.05:
        score += 5



    # Avoid weak setups

    if price < sma50:
        score -= 10



    # Keep score between 0-100

    score = max(
        0,
        min(score,100)
    )


    return score