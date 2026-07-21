"""
Compares Cortex's live entry logic (stock_scanner.analyze_stock scoring)
against two exit strategies on real historical data:

  A) CURRENT: fixed STOP_LOSS_PERCENT / TAKE_PROFIT_RATIO from config.py
  B) PROPOSED: ATR-based stop/target, same 1:3 risk:reward multiple

Each symbol is backtested independently with its own $10k, one position
at a time, to isolate the effect of the exit mechanism from portfolio
sizing/correlation effects.
"""

import sys
sys.path.insert(0, r"D:\AI-Trader")

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from dotenv import load_dotenv
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import os
from datetime import datetime, timedelta

import config
from stock_scanner import stocks

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

STARTING_CASH = 10000
POSITION_FRACTION = 0.5
ENTRY_SCORE_THRESHOLD = 75  # matches the live "SKIPPING SCORE TOO LOW" gate
ATR_STOP_MULT = 1.5
ATR_TARGET_MULT = ATR_STOP_MULT * config.TAKE_PROFIT_RATIO


def get_history(symbol):
    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=730),
        end=datetime.now(),
        feed=DataFeed.IEX
    )
    bars = client.get_stock_bars(request)
    data = bars.df.reset_index()

    data["SMA20"] = SMAIndicator(data["close"], window=20).sma_indicator()
    data["SMA50"] = SMAIndicator(data["close"], window=50).sma_indicator()
    data["RSI"] = RSIIndicator(data["close"], window=14).rsi()
    data["ATR"] = AverageTrueRange(
        high=data["high"], low=data["low"], close=data["close"], window=14
    ).average_true_range()
    data["VOL_AVG20"] = data["volume"].rolling(20).mean()

    return data


def cortex_score(data, i):
    """Reproduces stock_scanner.analyze_stock's scoring, using only
    data available up to index i (no lookahead)."""

    row = data.iloc[i]
    price = float(row["close"])
    sma20 = float(row["SMA20"])
    sma50 = float(row["SMA50"])
    rsi = float(row["RSI"])
    atr = float(row["ATR"])
    vol_avg = float(row["VOL_AVG20"])

    if vol_avg == 0 or any(map(lambda x: x != x, [sma20, sma50, rsi, atr, vol_avg])):
        return 0

    volume_strength = float(row["volume"]) / vol_avg

    if i < 21:
        return 0

    five_day_change = (price - float(data.iloc[i - 5]["close"])) / float(data.iloc[i - 5]["close"]) * 100
    twenty_day_change = (price - float(data.iloc[i - 20]["close"])) / float(data.iloc[i - 20]["close"]) * 100

    score = 0

    if price > sma20:
        score += 20
    if sma20 > sma50:
        score += 20

    if 50 <= rsi <= 65:
        score += 20
    elif rsi > 70:
        score -= 10

    if volume_strength > 1.2:
        score += 15
    elif volume_strength < .8:
        score -= 5

    if five_day_change > 3:
        score += 10
    if twenty_day_change > 10:
        score += 15

    volatility = atr / price if price else 0
    if volatility > .05:
        score -= 10

    return max(0, min(score, 100))


def run(data, mode):
    """mode: 'fixed' or 'atr'"""

    cash = STARTING_CASH
    shares = 0
    entry = 0
    stop = 0
    target = 0
    trades = []

    for i in range(len(data)):
        price = float(data.iloc[i]["close"])

        if shares == 0:
            if i < 25:
                continue

            score = cortex_score(data, i)
            rsi = float(data.iloc[i]["RSI"])
            atr = float(data.iloc[i]["ATR"])

            if score >= ENTRY_SCORE_THRESHOLD and rsi <= 75:
                shares = int((cash * POSITION_FRACTION) / price)
                if shares <= 0:
                    continue

                entry = price
                cash -= shares * price

                if mode == "fixed":
                    stop = entry * (1 - config.STOP_LOSS_PERCENT)
                    target = entry * (1 + config.STOP_LOSS_PERCENT * config.TAKE_PROFIT_RATIO)
                else:
                    stop = entry - ATR_STOP_MULT * atr
                    target = entry + ATR_TARGET_MULT * atr

                trades.append({"type": "BUY", "price": price})

        else:
            if price <= stop or price >= target:
                cash += shares * price
                pnl_pct = (price - entry) / entry
                trades.append({"type": "SELL", "price": price, "profit": pnl_pct})
                shares = 0

    final = cash + shares * float(data.iloc[-1]["close"])
    return final, trades


def summarize(symbol, mode, final, trades):
    sells = [t["profit"] for t in trades if t["type"] == "SELL"]
    wins = [x for x in sells if x > 0]
    ret_pct = (final - STARTING_CASH) / STARTING_CASH * 100
    win_rate = (len(wins) / len(sells) * 100) if sells else 0
    return {
        "symbol": symbol,
        "mode": mode,
        "return_pct": ret_pct,
        "trades": len(sells),
        "win_rate": win_rate,
    }


results = []

for symbol in stocks:
    try:
        data = get_history(symbol)
        if len(data) < 100:
            print(symbol, "SKIPPED: not enough data")
            continue

        final_fixed, trades_fixed = run(data, "fixed")
        final_atr, trades_atr = run(data, "atr")

        r_fixed = summarize(symbol, "fixed", final_fixed, trades_fixed)
        r_atr = summarize(symbol, "atr", final_atr, trades_atr)
        results.append(r_fixed)
        results.append(r_atr)

        print(f"\n{symbol}")
        print(f"  FIXED : return {r_fixed['return_pct']:+.2f}%  trades {r_fixed['trades']:3d}  win rate {r_fixed['win_rate']:.1f}%")
        print(f"  ATR   : return {r_atr['return_pct']:+.2f}%  trades {r_atr['trades']:3d}  win rate {r_atr['win_rate']:.1f}%")

    except Exception as e:
        print(symbol, "ERROR:", e)


def agg(mode):
    rows = [r for r in results if r["mode"] == mode]
    if not rows:
        return None
    avg_return = sum(r["return_pct"] for r in rows) / len(rows)
    total_trades = sum(r["trades"] for r in rows)
    avg_win_rate = sum(r["win_rate"] for r in rows if r["trades"] > 0) / max(1, len([r for r in rows if r["trades"] > 0]))
    beaten = sum(1 for r in rows if r["return_pct"] > 0)
    return avg_return, total_trades, avg_win_rate, beaten, len(rows)


print("\n\n===================== SUMMARY (avg across universe) =====================")
for mode in ["fixed", "atr"]:
    stats = agg(mode)
    if stats:
        avg_return, total_trades, avg_win_rate, beaten, n = stats
        print(f"{mode.upper():6s}  avg return {avg_return:+.2f}%   total trades {total_trades:4d}   avg win rate {avg_win_rate:.1f}%   symbols profitable {beaten}/{n}")
