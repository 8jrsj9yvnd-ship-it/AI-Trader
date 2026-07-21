from memory import save_trade, read_memory


save_trade(
    "AAPL",
    "BUY",
    "+$25",
    "Trend followed SMA breakout"
)


print(read_memory())