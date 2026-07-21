from stock_ranker import score_stock
from stock_scanner import analyze_stock, stocks


MIN_SCORE = 70
MAX_RESULTS = 5



def get_ranked_stocks():

    results = []


    for symbol in stocks:

        try:

            data = analyze_stock(symbol)

            score = score_stock(data)

            data["score"] = score


            if score >= MIN_SCORE:

                if score >= 90:
                    data["confidence"] = "HIGH"

                elif score >= 80:
                    data["confidence"] = "MEDIUM"

                else:
                    data["confidence"] = "LOW"


                results.append(data)



        except Exception as e:

            print(
                symbol,
                "ERROR:",
                e
            )



    results.sort(
        key=lambda x:x["score"],
        reverse=True
    )


    return results[:MAX_RESULTS]




if __name__ == "__main__":


    print("""
=====================================
       CORTEX SMART SCANNER
=====================================
""")


    ranked = get_ranked_stocks()


    for stock in ranked:

        print(
            stock["symbol"],
            "| Score:",
            stock["score"],
            "| Confidence:",
            stock["confidence"],
            "| Price:",
            stock["price"],
            "| RSI:",
            stock["rsi"]
        )