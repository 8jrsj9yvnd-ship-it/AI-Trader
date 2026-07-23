"""
Portfolio-level backtest that replicates the CURRENT live trading logic in
autonomous_controller.py (as of the 2026-07-23 rewrite that removed the LLM
gate): scan the full watchlist each day, rank by score, and enter EVERY
candidate that clears the score/RSI/volume gates -- not just one -- up to
MAX_OPEN_POSITIONS, sized via the real risk_manager.calculate_position_size().
Single shared capital pool across the whole watchlist.

This is NOT the same methodology as backtester_entry_sweep.py /
backtester_atr_comparison.py, which backtest each symbol independently with
its own $10k (never modeling the position-count cap or shared buying power).
Those validated the entry thresholds; this validates what the live bot
actually does with them now. The original portfolio-level sim referenced in
config.py's tuning comments (portfolio_final.py etc.) lived outside this repo
and no longer exists, so this rebuilds that methodology against current code.

Simplifications (inherited from the existing backtester scripts, for
comparability): daily bars only, exits checked against daily close (not
intraday touch), no daily-loss circuit breaker (can't be modeled without
intraday data), execution assumed at that day's close with no slippage.
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
from risk_manager import calculate_position_size
from stock_scanner import stocks

load_dotenv()

client = StockHistoricalDataClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY")
)

STARTING_CASH = 100_000
DAYS = 730


def get_history(symbol):
    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=DAYS),
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
    data["date"] = data["timestamp"].dt.date

    return data.set_index("date")


def cortex_score(row, prev5, prev20):
    price = float(row["close"])
    sma20 = float(row["SMA20"])
    sma50 = float(row["SMA50"])
    rsi = float(row["RSI"])
    atr = float(row["ATR"])
    vol_avg = float(row["VOL_AVG20"])

    if vol_avg == 0 or any(x != x for x in [sma20, sma50, rsi, atr, vol_avg, prev5, prev20]):
        return None

    volume_strength = float(row["volume"]) / vol_avg
    five_day_change = (price - prev5) / prev5 * 100
    twenty_day_change = (price - prev20) / prev20 * 100

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

    score = max(0, min(score, 100))
    return score, rsi, atr, volume_strength


print("Fetching data for watchlist + SPY...")

all_data = {}
for symbol in stocks + ["SPY"]:
    try:
        d = get_history(symbol)
        if len(d) >= 100:
            all_data[symbol] = d
        else:
            print(symbol, "SKIPPED: not enough data")
    except Exception as e:
        print(symbol, "ERROR:", e)

spy = all_data.pop("SPY")
master_dates = sorted(spy.index)

print(f"Loaded {len(all_data)} symbols over {len(master_dates)} trading days.\n")


def run_portfolio_sim(start_idx, end_idx, threshold, verbose=False, slippage_bps=0):
    """slippage_bps: basis points of unfavorable slippage applied to every
    fill (buy pays more, sell receives less), to test how much of the edge
    depends on the backtest's default zero-friction assumption -- real
    orders (especially in the thinner names on the watchlist, and anything
    filled outside regular hours) won't fill exactly at the recorded close."""

    slip = slippage_bps / 10_000

    cash = STARTING_CASH
    positions = {}  # symbol -> {shares, entry, stop, target}
    trades = []
    equity_curve = []

    dates = master_dates[start_idx:end_idx]

    for d in dates:

        # mark-to-market equity using each held symbol's close today (fall
        # back to entry price if a data gap on this exact date)
        equity = cash
        for sym, pos in positions.items():
            px = float(all_data[sym].loc[d, "close"]) if d in all_data[sym].index else pos["entry"]
            equity += pos["shares"] * px
        equity_curve.append((d, equity))

        # manage exits
        for sym in list(positions.keys()):
            data = all_data[sym]
            if d not in data.index:
                continue
            price = float(data.loc[d, "close"])
            pos = positions[sym]
            if price <= pos["stop"] or price >= pos["target"]:
                fill_price = price * (1 - slip)
                cash += pos["shares"] * fill_price
                pnl_pct = (fill_price - pos["entry"]) / pos["entry"]
                trades.append({"symbol": sym, "profit_pct": pnl_pct})
                del positions[sym]

        # regime filter -- SPY close > its 50d SMA, exactly like
        # market_filter.market_is_good()
        if d not in spy.index:
            continue
        spy_sma50 = spy.loc[d, "SMA50"]
        if spy_sma50 != spy_sma50 or not (spy.loc[d, "close"] > spy_sma50):
            continue

        if len(positions) >= config.MAX_OPEN_POSITIONS:
            continue

        # rank all non-held symbols with valid data this day
        candidates = []
        for sym, data in all_data.items():
            if sym in positions or d not in data.index:
                continue
            i = data.index.get_loc(d)
            if i < 25:
                continue
            row = data.loc[d]
            prev5 = float(data.iloc[i - 5]["close"])
            prev20 = float(data.iloc[i - 20]["close"])
            result = cortex_score(row, prev5, prev20)
            if result is None:
                continue
            score, rsi, atr, vol_strength = result
            if score >= threshold and rsi <= 75 and vol_strength >= config.MIN_VOLUME_STRENGTH:
                candidates.append((score, sym, float(row["close"]), atr))

        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, sym, price, atr in candidates:
            if len(positions) >= config.MAX_OPEN_POSITIONS:
                break
            if price <= 0:
                continue

            fill_price = price * (1 + slip)

            sizing = calculate_position_size(equity, price, atr=atr)
            shares = min(sizing.get("shares", 0), config.MAX_SHARES_PER_TRADE)
            cost = shares * fill_price

            if shares <= 0 or cost > cash:
                continue

            cash -= cost
            positions[sym] = {
                "shares": shares,
                "entry": fill_price,
                "stop": sizing["stop_loss"],
                "target": sizing["take_profit"],
            }

    # liquidate remaining positions at final close
    final_d = dates[-1]
    for sym, pos in positions.items():
        data = all_data[sym]
        price = float(data.loc[final_d, "close"]) if final_d in data.index else pos["entry"]
        fill_price = price * (1 - slip)
        cash += pos["shares"] * fill_price
        pnl_pct = (fill_price - pos["entry"]) / pos["entry"]
        trades.append({"symbol": sym, "profit_pct": pnl_pct})

    final_equity = cash
    wins = [t for t in trades if t["profit_pct"] > 0]

    max_dd = 0
    peak = STARTING_CASH
    for _, eq in equity_curve:
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak)

    return {
        "return_pct": (final_equity - STARTING_CASH) / STARTING_CASH * 100,
        "trades": len(trades),
        "win_rate": (len(wins) / len(trades) * 100) if trades else 0,
        "max_drawdown_pct": max_dd * 100,
        "final_equity": final_equity,
    }


print("===================== FULL PERIOD =====================")
r = run_portfolio_sim(0, len(master_dates), config.MIN_ENTRY_SCORE)
print(f"threshold={config.MIN_ENTRY_SCORE}  return {r['return_pct']:+7.2f}%  "
      f"trades {r['trades']:4d}  win rate {r['win_rate']:5.1f}%  max DD {r['max_drawdown_pct']:5.2f}%  "
      f"final equity ${r['final_equity']:,.2f}")

print("\n===================== WALK-FORWARD SPLIT (first half / second half) =====================")
mid = len(master_dates) // 2
first = run_portfolio_sim(0, mid, config.MIN_ENTRY_SCORE)
second = run_portfolio_sim(mid, len(master_dates), config.MIN_ENTRY_SCORE)
print(f"First half:  return {first['return_pct']:+7.2f}%  trades {first['trades']:4d}  "
      f"win rate {first['win_rate']:5.1f}%  max DD {first['max_drawdown_pct']:5.2f}%")
print(f"Second half: return {second['return_pct']:+7.2f}%  trades {second['trades']:4d}  "
      f"win rate {second['win_rate']:5.1f}%  max DD {second['max_drawdown_pct']:5.2f}%")

print("\n===================== THRESHOLD SANITY CHECK (full period) =====================")
for threshold in [65, 70, 75, 80, 85, 90]:
    r = run_portfolio_sim(0, len(master_dates), threshold)
    print(f"threshold={threshold:3d}  return {r['return_pct']:+7.2f}%  trades {r['trades']:4d}  "
          f"win rate {r['win_rate']:5.1f}%  max DD {r['max_drawdown_pct']:5.2f}%")

print("\n===================== WALK-FORWARD CHECK ON CANDIDATE THRESHOLDS =====================")
for threshold in [80, 85, 90]:
    f = run_portfolio_sim(0, mid, threshold)
    s = run_portfolio_sim(mid, len(master_dates), threshold)
    print(f"threshold={threshold:3d}  first half {f['return_pct']:+7.2f}% ({f['trades']:3d} trades)   "
          f"second half {s['return_pct']:+7.2f}% ({s['trades']:3d} trades)   "
          f"{'BOTH POSITIVE' if f['return_pct']>0 and s['return_pct']>0 else 'FAILS split'}")


def sweep(param_name, values, threshold=None):
    """One-at-a-time parameter sweep, walk-forward validated, holding every
    other config value at its current live setting. Deliberately not a grid
    search -- with ~500 days / 20 symbols, combinatorial tuning would just
    curve-fit noise instead of finding a real edge."""

    threshold = threshold if threshold is not None else config.MIN_ENTRY_SCORE
    original = getattr(config, param_name)

    print(f"\n===================== SWEEP: {param_name} (threshold={threshold}, current live={original}) =====================")

    for v in values:
        setattr(config, param_name, v)
        full = run_portfolio_sim(0, len(master_dates), threshold)
        f = run_portfolio_sim(0, mid, threshold)
        s = run_portfolio_sim(mid, len(master_dates), threshold)
        flag = "BOTH POSITIVE" if f["return_pct"] > 0 and s["return_pct"] > 0 else "FAILS split"
        marker = "  <- current live" if v == original else ""
        print(f"{param_name}={v!s:>6}  full {full['return_pct']:+7.2f}%  "
              f"1H {f['return_pct']:+6.2f}% ({f['trades']:3d}tr)  2H {s['return_pct']:+6.2f}% ({s['trades']:3d}tr)  "
              f"DD {full['max_drawdown_pct']:5.2f}%  win {full['win_rate']:5.1f}%  {flag}{marker}")

    setattr(config, param_name, original)


sweep("ATR_STOP_MULTIPLIER", [1.0, 1.25, 1.5, 1.75, 2.0, 2.5])
sweep("TAKE_PROFIT_RATIO", [2.0, 2.5, 3.0, 3.5, 4.0, 5.0])
sweep("MAX_SHARES_PER_TRADE", [50, 75, 100, 125, 150, 200])
sweep("MAX_OPEN_POSITIONS", [5, 8, 10, 12, 15, 18, 20])
sweep("MIN_VOLUME_STRENGTH", [0.9, 1.0, 1.1, 1.2, 1.3])
sweep("RISK_PER_TRADE", [0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02])


print(f"\n===================== SLIPPAGE SENSITIVITY (threshold={config.MIN_ENTRY_SCORE}) =====================")
print("Every other test above assumes a free, frictionless fill exactly at the recorded")
print("close. This applies unfavorable slippage to every entry AND exit to see how much")
print("of the edge is real vs. an artifact of that zero-cost assumption -- the honest")
print("worst-case proxy for extended-hours fills, which can't be backtested directly")
print("since only daily bars are available (no real intraday order-book/spread data).")
for bps in [0, 5, 10, 20, 35, 50, 75, 100]:
    full = run_portfolio_sim(0, len(master_dates), config.MIN_ENTRY_SCORE, slippage_bps=bps)
    f = run_portfolio_sim(0, mid, config.MIN_ENTRY_SCORE, slippage_bps=bps)
    s = run_portfolio_sim(mid, len(master_dates), config.MIN_ENTRY_SCORE, slippage_bps=bps)
    flag = "BOTH POSITIVE" if f["return_pct"] > 0 and s["return_pct"] > 0 else "FAILS split"
    print(f"slippage={bps:3d}bps  full {full['return_pct']:+7.2f}%  "
          f"1H {f['return_pct']:+6.2f}%  2H {s['return_pct']:+6.2f}%  DD {full['max_drawdown_pct']:5.2f}%  {flag}")
