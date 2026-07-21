from market_filter import market_is_good
def score_stock(stock):

    score = 40
    
    market_good, market_reason = market_is_good()

    if market_good:
        score += 5
    else:
        score -= 15

    price = stock["price"]
    sma20 = stock["sma20"]
    sma50 = stock["sma50"]
    rsi = stock["rsi"]

    # =====================
    # TREND ANALYSIS
    # =====================

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
    else:
        score -= 10


    # =====================
    # RSI QUALITY
    # =====================

    if 50 <= rsi <= 60:
        score += 15

    elif 60 < rsi <= 70:
        score += 10

    elif 70 < rsi <= 80:
        score += 0

    elif rsi > 80:
        score -= 20

    elif rsi < 40:
        score -= 15


    # =====================
    # MOMENTUM CONFIRMATION
    # =====================

    if price > sma20 * 1.03:
        score += 5


    if price > sma20 * 1.08:
        score -= 5   # too extended


    # =====================
    # RISK CONTROL
    # =====================

    if rsi > 75 and price > sma20 * 1.05:
        score -= 10


    score = max(
    0,
    min(score,95)
)


    return score