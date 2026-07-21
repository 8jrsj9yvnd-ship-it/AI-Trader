from stock_ranker import score_stock
from stock_scanner import analyze_stock, stocks


def get_ranked_stocks():

    results = []

    for symbol in stocks:
        try:
            data = analyze_stock(symbol)

            score = score_stock(data)

            data["score"] = score

            results.append(data)

        except Exception as e:
            print(symbol, "ERROR:", e)


    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results


# Test when running directly
if __name__ == "__main__":

    print("\n===== TOP OPPORTUNITIES =====\n")

    ranked = get_ranked_stocks()

    for stock in ranked:

        print(
            stock["symbol"],
            "| Score:",
            stock["score"],
            "| Price:",
            stock["price"],
            "| RSI:",
            stock["rsi"]
        )