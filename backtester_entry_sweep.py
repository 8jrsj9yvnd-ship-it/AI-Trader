"""
Extends backtester_atr_comparison.py's harness to test two questions
about Cortex's ENTRY logic (using the now-live ATR-based exits, since
that's the current best-known exit mechanism):

  1) Is ENTRY_SCORE_THRESHOLD (currently 75 live) well-tuned, or would a
     different cutoff produce better risk-adjusted results?
  2) Does gating entries on market_filter.py's regime check (SPY > SMA50)
     actually improve results, or does it just cut trade count?

Each symbol is backtested independently with its own $10k, one position
at a time, matching the methodology of backtester_atr_comparison.py.
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
ATR_STOP_MULT = config.ATR_STOP_MULTIPLIER
ATR_TARGET_MULT = ATR_STOP_MULT * config.TAKE_PROFIT_RATIO

THRESHOLDS = [65, 70, 75, 80, 85]


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


def get_spy_regime():
    """Returns a dict: date -> True/False (SPY > its 50d SMA that day)."""
    request = StockBarsRequest(
        symbol_or_symbols=["SPY"],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=730),
        end=datetime.now(),
        feed=DataFeed.IEX
    )
    bars = client.get_stock_bars(request)
    data = bars.df.reset_index()
    data["SMA50"] = SMAIndicator(data["close"], window=50).sma_indicator()

    regime = {}
    for _, row in data.iterrows():
        d = row["timestamp"].date()
        if row["SMA50"] == row["SMA50"]:  # not NaN
            regime[d] = bool(row["close"] > row["SMA50"])

    return regime


def cortex_score(data, i):
    row = data.iloc[i]
    price = float(row["close"])
    sma20 = float(row["SMA20"])
    sma50 = float(row["SMA50"])
    rsi = float(row["RSI"])
    atr = float(row["ATR"])
    vol_avg = float(row["VOL_AVG20"])

    if vol_avg == 0 or any(map(lambda x: x != x, [sma20, sma50, rsi, atr, vol_avg])):
        return 0

    if i < 21:
        return 0

    volume_strength = float(row["volume"]) / vol_avg

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


def run(data, threshold, regime, require_good_regime):
    cash = STARTING_CASH
    shares = 0
    entry = 0
    stop = 0
    target = 0
    trades = []

    for i in range(len(data)):
        price = float(data.iloc[i]["close"])
        ts = data.iloc[i]["timestamp"]
        d = ts.date() if hasattr(ts, "date") else None

        if shares == 0:
            if i < 25:
                continue

            if require_good_regime:
                is_good = regime.get(d)
                if is_good is not True:
                    continue

            score = cortex_score(data, i)
            rsi = float(data.iloc[i]["RSI"])
            atr = float(data.iloc[i]["ATR"])

            if score >= threshold and rsi <= 75:
                shares = int((cash * POSITION_FRACTION) / price)
                if shares <= 0:
                    continue

                entry = price
                cash -= shares * price
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
    sells = [t["profit"] for t in trades if t["type"] == "SELL"]
    wins = [x for x in sells if x > 0]
    return {
        "return_pct": (final - STARTING_CASH) / STARTING_CASH * 100,
        "trades": len(sells),
        "win_rate": (len(wins) / len(sells) * 100) if sells else 0,
    }


print("Fetching SPY regime data...")
regime = get_spy_regime()

all_data = {}
for symbol in stocks:
    try:
        d = get_history(symbol)
        if len(d) >= 100:
            all_data[symbol] = d
        else:
            print(symbol, "SKIPPED: not enough data")
    except Exception as e:
        print(symbol, "ERROR:", e)

print(f"\nLoaded {len(all_data)} symbols.\n")

print("===================== ENTRY THRESHOLD SWEEP (no regime filter) =====================")
for threshold in THRESHOLDS:
    rows = []
    for symbol, data in all_data.items():
        rows.append(run(data, threshold, regime, require_good_regime=False))

    avg_return = sum(r["return_pct"] for r in rows) / len(rows)
    total_trades = sum(r["trades"] for r in rows)
    traded = [r for r in rows if r["trades"] > 0]
    avg_win_rate = sum(r["win_rate"] for r in traded) / max(1, len(traded))
    profitable = sum(1 for r in rows if r["return_pct"] > 0)

    print(f"threshold={threshold:3d}  avg return {avg_return:+6.2f}%   total trades {total_trades:4d}   avg win rate {avg_win_rate:5.1f}%   profitable {profitable}/{len(rows)}")

print(f"\n===================== REGIME FILTER ON/OFF (threshold={config.MIN_ENTRY_SCORE}, live default) =====================")
for require_regime in [False, True]:
    rows = []
    for symbol, data in all_data.items():
        rows.append(run(data, config.MIN_ENTRY_SCORE, regime, require_good_regime=require_regime))

    avg_return = sum(r["return_pct"] for r in rows) / len(rows)
    total_trades = sum(r["trades"] for r in rows)
    traded = [r for r in rows if r["trades"] > 0]
    avg_win_rate = sum(r["win_rate"] for r in traded) / max(1, len(traded))
    profitable = sum(1 for r in rows if r["return_pct"] > 0)

    label = "regime filter ON " if require_regime else "regime filter OFF"
    print(f"{label}  avg return {avg_return:+6.2f}%   total trades {total_trades:4d}   avg win rate {avg_win_rate:5.1f}%   profitable {profitable}/{len(rows)}")
