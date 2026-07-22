# Risk Settings
RISK_PER_TRADE = 0.01  # backtested 2026-07-21: no measurable effect from 0.005-0.02 in a portfolio-level sim,
# because MAX_SHARES_PER_TRADE is the actual binding constraint on nearly every trade, not this risk formula.
# Left unchanged.
MAX_DAILY_LOSS = 0.03
MAX_OPEN_POSITIONS = 15  # backtested 2026-07-21 with a portfolio-level sim (shared capital pool across all
# watchlist symbols, not independent per-symbol accounts): 5 was capital-constrained. Walk-forward split
# (first/second half of ~2yr history, tested independently, on the corrected MIN_ENTRY_SCORE=80 base below)
# shows monotonic improvement 5->15 in BOTH halves (+4.81/+3.95% at 5 vs +8.91/+7.83% at 15), then plateaus
# (20 = full watchlist size, flat vs 15). See scratchpad portfolio_backtest.py / portfolio_final*.py.

# Trade Settings
STOP_LOSS_PERCENT = 0.02
TAKE_PROFIT_RATIO = 3.0
MAX_SHARES_PER_TRADE = 100  # backtested 2026-07-21: the old flat 20-share cap was overriding the risk-based
# sizing formula (which already caps at 10% of equity) on nearly every trade, arbitrarily shrinking positions
# regardless of price/account size. Walk-forward split (on the corrected threshold=80 base) shows monotonic
# improvement in BOTH halves up to 100 (+13.37%/+10.68%), then plateaus (150-250 flat vs 100). Real tradeoff:
# max drawdown rose from ~4.5% (at max_shares=20) to ~9.0% -- bigger positions, bigger swings, not free money.
ATR_STOP_MULTIPLIER = 1.5  # stop = entry - ATR_STOP_MULTIPLIER * ATR (falls back to STOP_LOSS_PERCENT if no ATR)
# CORRECTED 2026-07-21: briefly changed to 1.0 based on a backtest that omitted a real live-only gate (see
# MIN_ENTRY_SCORE note below) -- reverted to the original 1.5 once that gate was properly modeled, since 1.5
# clearly beat 1.0 on the corrected methodology (part of the threshold=80/stop=1.5 result documented below).

# Scanner Settings
MIN_CONFIDENCE = 80
MIN_VOLUME_STRENGTH = 1.1  # backtested 2026-07-21: was hardcoded as 1.0 directly in autonomous_controller.py
# (moved here). Walk-forward split at the final threshold=80/stop=1.5/max_open=15/shares=100 base shows 1.1
# beats 1.0 in BOTH halves (+14.11%/+11.38% vs +13.37%/+10.68%) AND lowers drawdown (7.96% vs 9.05%) -- a
# strict improvement, not a return/risk tradeoff. Values below 1.0 (0.6-0.9) were all worse. See scratchpad
# volume_gate_sweep.py.
MIN_ENTRY_SCORE = 80  # CORRECTED 2026-07-21: briefly lowered to 55 after a backtest suggested it was too
# strict. That backtest (and the portfolio-level sim built to refine it) both omitted a real, separate, live-only
# gate: autonomous_controller.py's "if selected['volume_strength'] < 1.0: SKIPPING WEAK VOLUME" check, which
# backtester_entry_sweep.py's cortex_score() only used as a soft scoring input (+15/-5), never a hard cutoff.
# Once that gate was added to the portfolio-level sim to match live behavior, results reversed: threshold=80
# clearly beat 55/65/70 on a walk-forward split (both halves positive, +4.81%/+3.95%, lowest drawdown of any
# candidate at ~5.3% before the position-sizing changes above), while 65 and 70 both had a NEGATIVE second
# half (overfit to a run that didn't model a real constraint). Reverted to the original 80.
# See scratchpad portfolio_final.py / portfolio_final2.py for the corrected methodology and full numbers.
