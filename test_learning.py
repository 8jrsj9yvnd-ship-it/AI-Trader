from cortex_learning import log_trade, learning_summary

log_trade(
    "AAPL",
    330,
    335,
    5,
    "Momentum above moving averages"
)

print(learning_summary())