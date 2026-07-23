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

# Extended Hours Settings
ENABLE_EXTENDED_HOURS = True  # trade pre-market (4:00-9:30 ET) and after-hours (16:00-20:00 ET) too
EXTENDED_HOURS_LIMIT_BUFFER = 0.002  # marketable limit buffer -- Alpaca rejects market orders outside
# regular hours, so extended-hours entries/exits use a limit price this far past the reference price

# Scanner Settings
# (MIN_CONFIDENCE removed 2026-07-23: it gated an LLM self-reported confidence
# score that was never backtested and could only veto trades the validated
# score/RSI/volume thresholds below would otherwise take. See autonomous_controller.py.)
MIN_VOLUME_STRENGTH = 1.1  # backtested 2026-07-21: was hardcoded as 1.0 directly in autonomous_controller.py
# (moved here). Walk-forward split at the final threshold=80/stop=1.5/max_open=15/shares=100 base shows 1.1
# beats 1.0 in BOTH halves (+14.11%/+11.38% vs +13.37%/+10.68%) AND lowers drawdown (7.96% vs 9.05%) -- a
# strict improvement, not a return/risk tradeoff. Values below 1.0 (0.6-0.9) were all worse. See scratchpad
# volume_gate_sweep.py.
MIN_ENTRY_SCORE = 85  # RAISED 2026-07-23: autonomous_controller.py was rewritten to drop the LLM
# approval gate, which previously only ever veto'd trades (never approved ones that failed the
# thresholds below) and capped entries to one per cycle regardless of how many candidates qualified.
# Live behavior now enters every qualifying candidate per cycle, up to MAX_OPEN_POSITIONS -- a
# materially different trading pattern than what 80 was originally tuned against, so it was re-swept.
# backtester_live_portfolio.py rebuilds the portfolio-level methodology (shared capital pool, real
# risk_manager sizing) against current live logic over ~2yr/501 trading days: 85 beat 80 on every axis,
# not just a return/risk tradeoff -- higher full-period return (+31.33% vs +30.17%), BOTH walk-forward
# halves positive with the second half stronger than the first (+14.81%/+12.31%, so the edge isn't
# decaying), higher win rate (47.8% vs 43.5%), and lower max drawdown (5.84% vs 8.02%). 90 also passed
# both halves but on only 22-26 trades per half -- too thin a sample to trust over 85's 44-48.
# CORRECTED 2026-07-21 history (why it was 80 before): briefly lowered to 55 after a backtest that
# omitted a real, separate, live-only gate: autonomous_controller.py's "if selected['volume_strength']
# < 1.0: SKIPPING WEAK VOLUME" check, which backtester_entry_sweep.py's cortex_score() only used as a
# soft scoring input (+15/-5), never a hard cutoff. Once that gate was modeled, results reversed:
# threshold=80 beat 55/65/70 on a walk-forward split, while 65 and 70 both had a negative second half
# (overfit to a run that didn't model a real constraint).
