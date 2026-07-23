import os
import json as _json
import time as _time
import ollama
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from cortex_learning import learning_summary, load_memory

load_dotenv()

LOCAL_TZ = ZoneInfo("America/Los_Angeles")

# Real deployed URL -- do not let the model "answer" this from its own
# knowledge. It has no grounding for it and will hallucinate a plausible-
# looking fake (observed 2026-07-23: it invented the literal placeholder
# text "link_to_streamlit_app" as a real link when asked). Always inject
# this string into context instead.
DASHBOARD_URL = "https://ai-trader-mdaen73appykrcvqq2y5zgt.streamlit.app/"

alpaca = TradingClient(
    os.getenv("ALPACA_API_KEY"),
    os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)


def get_alpaca_context():

    try:
        account = alpaca.get_account()
        positions = alpaca.get_all_positions()

        context = f"""
ALPACA ACCOUNT DATA:

Cash:
${account.cash}

Buying Power:
${account.buying_power}

Equity:
${account.equity}

OPEN POSITIONS:
"""

        if positions:
            for p in positions:
                context += f"""
{p.symbol}
Shares: {p.qty}
Entry Price: {p.avg_entry_price}
Current Price: {p.current_price}
Unrealized P/L: ${p.unrealized_pl}
"""
        else:
            context += "\nNo open positions."

        return context

    except Exception as e:
        return f"Unable to retrieve Alpaca data: {e}"


CORTEX_SYSTEM_PROMPT = (
    "You are Cortex, a helpful AI assistant and trading assistant. "
    "You can answer general questions, explain concepts, help with coding, "
    "and discuss investing and trading. Be concise, accurate, and conversational. "
    "Your training data has a fixed cutoff and does not include real-world events "
    "after that point -- for anything time-sensitive (current events, who holds an "
    "office, recent news) outside what's given to you in context below, say you "
    "don't have reliable up-to-date knowledge of it rather than guessing.\n\n"
    "When you're given data (tool results or context above) that includes an "
    "'explanation' field or similar plain-language description, relay that "
    "description faithfully -- do not invent a different mechanism, method, or "
    "reasoning that sounds plausible but isn't actually what the data says. "
    "If the data doesn't cover something you're asked, say you don't know rather "
    "than filling the gap with a guess."
)


def get_time_context():
    now = datetime.now(LOCAL_TZ)
    return f"Current date/time: {now.strftime('%A, %B %d, %Y, %I:%M %p %Z')}"


def get_learning_context_summary():
    try:
        return learning_summary()
    except Exception as e:
        return f"Unable to retrieve trading performance history: {e}"


# ============================================================
# TOOLS -- on-demand data lookups the model can call mid-answer
# instead of guessing. The context injected into every prompt
# (time, dashboard link, full account snapshot, performance
# summary) covers the common asks for free; these cover anything
# more specific: an arbitrary ticker, a single symbol's trade
# history, the actual strategy config, precise market session,
# or the current scanner rankings.
# ============================================================

_scanner_cache = {"data": None, "ts": 0}


def _tool_get_stock_analysis(symbol):
    from stock_scanner import analyze_stock
    try:
        return _json.dumps(analyze_stock(symbol.upper()))
    except Exception as e:
        return _json.dumps({"error": f"Could not analyze {symbol}: {e}"})


def _tool_get_position(symbol):
    try:
        p = alpaca.get_open_position(symbol.upper())
        return _json.dumps({
            "symbol": p.symbol,
            "qty": p.qty,
            "avg_entry_price": p.avg_entry_price,
            "current_price": p.current_price,
            "unrealized_pl": p.unrealized_pl,
            "unrealized_plpc": p.unrealized_plpc,
        })
    except Exception:
        return _json.dumps({"held": False, "detail": f"No open position in {symbol.upper()}"})


def _tool_get_trade_history(symbol=None, limit=5):
    try:
        memory = load_memory()
        completed = [t for t in memory if "profit_loss" in t]
        if symbol:
            completed = [t for t in completed if t.get("symbol", "").upper() == symbol.upper()]
        completed = list(reversed(completed))[:max(1, min(int(limit or 5), 25))]
        return _json.dumps(completed)
    except Exception as e:
        return _json.dumps({"error": str(e)})


def _tool_get_strategy_settings():
    # Plain-English "explanation" fields alongside the raw numbers -- a small
    # local model paraphrasing bare numbers has been observed inventing a
    # mechanism that isn't real (e.g. claiming take-profit uses "a moving
    # average crossover system" when it's actually ATR-based/ratio-based).
    # Giving it the correct sentence directly leaves much less room to guess.
    import config
    return _json.dumps({
        "min_entry_score": {
            "value": config.MIN_ENTRY_SCORE,
            "explanation": f"A candidate must score at least {config.MIN_ENTRY_SCORE}/100 on Cortex's technical scoring (trend, momentum, volume, recent performance, volatility) to be eligible for entry.",
        },
        "min_volume_strength": {
            "value": config.MIN_VOLUME_STRENGTH,
            "explanation": f"Today's volume must be at least {config.MIN_VOLUME_STRENGTH}x the 20-day average volume, or the entry is skipped regardless of score.",
        },
        "stop_loss": {
            "atr_stop_multiplier": config.ATR_STOP_MULTIPLIER,
            "percent_fallback": config.STOP_LOSS_PERCENT,
            "explanation": f"Stop-loss is normally set at entry_price minus {config.ATR_STOP_MULTIPLIER}x the stock's Average True Range (a volatility-based distance, wider for more volatile stocks, tighter for calmer ones). If ATR isn't available, it falls back to a flat {config.STOP_LOSS_PERCENT*100:.0f}% below entry. It is NOT based on moving averages or crossovers.",
        },
        "take_profit": {
            "ratio_of_stop_distance": config.TAKE_PROFIT_RATIO,
            "explanation": f"Take-profit is set at a reward:risk ratio of {config.TAKE_PROFIT_RATIO}:1 -- i.e. {config.TAKE_PROFIT_RATIO}x as far above entry as the stop-loss is below it. If the stop is $2 below entry, the target is ${config.TAKE_PROFIT_RATIO*2:.0f} above entry. It is NOT based on moving averages or crossovers.",
        },
        "max_open_positions": {
            "value": config.MAX_OPEN_POSITIONS,
            "explanation": f"Cortex won't open more than {config.MAX_OPEN_POSITIONS} concurrent positions at once.",
        },
        "max_shares_per_trade": {
            "value": config.MAX_SHARES_PER_TRADE,
            "explanation": f"No single position exceeds {config.MAX_SHARES_PER_TRADE} shares, on top of the normal risk-based and 10%-of-equity position sizing caps.",
        },
        "risk_per_trade_pct": {
            "value": config.RISK_PER_TRADE,
            "explanation": f"Base position sizing targets risking {config.RISK_PER_TRADE*100:.1f}% of account equity per trade (before the max-shares/max-position-value caps, which are usually the binding constraint).",
        },
        "max_daily_loss_pct": {
            "value": config.MAX_DAILY_LOSS,
            "explanation": f"If the account is down {config.MAX_DAILY_LOSS*100:.0f}% or more versus yesterday's close, Cortex stops opening new positions for the rest of the day.",
        },
        "extended_hours_enabled": {
            "value": config.ENABLE_EXTENDED_HOURS,
            "explanation": "Extended-hours trading (pre-market/after-hours) is " + ("enabled" if config.ENABLE_EXTENDED_HOURS else "disabled") + " -- extended-hours orders use a marketable limit price instead of a market order.",
        },
        "scoring_rubric": {
            "explanation": (
                "Every candidate gets a 0-100 technical score (see stock_scanner.py): "
                "+20 if price is above its 20-day moving average, +20 if the 20-day average "
                "is above the 50-day (uptrend), +20 if RSI is 50-65 (healthy momentum) or "
                "-10 if RSI > 70 (overbought risk), +15 if today's volume is >1.2x the "
                "20-day average or -5 if <0.8x (weak volume), +10 if the 5-day change is "
                "over 3%, +15 if the 20-day change is over 10%, and -10 if ATR/price > 5% "
                "(high volatility -- wide, unpredictable price swings make stops more "
                "likely to get hit by noise rather than a real reversal, and make position "
                "sizing/risk harder to control, so it's penalized even though volatility "
                "isn't inherently bad). Score is clamped to 0-100."
            ),
        },
    })


def _tool_get_market_session():
    try:
        from market_hours import get_session
        return _json.dumps({"session": get_session()})
    except Exception as e:
        return _json.dumps({"error": str(e)})


def _tool_get_top_scanner_candidates(limit=5):
    from stock_scanner import analyze_stock, stocks as WATCHLIST

    now = _time.time()
    if _scanner_cache["data"] is None or now - _scanner_cache["ts"] > 300:
        results = []
        for sym in WATCHLIST:
            try:
                results.append(analyze_stock(sym))
            except Exception:
                pass
        results.sort(key=lambda x: x["score"], reverse=True)
        _scanner_cache["data"] = results
        _scanner_cache["ts"] = now

    limit = max(1, min(int(limit or 5), len(_scanner_cache["data"])))
    return _json.dumps(_scanner_cache["data"][:limit])


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_analysis",
            "description": (
                "Get live price, RSI, moving averages, volume strength, and Cortex's "
                "technical score/bias for ANY stock ticker, not just ones currently held "
                "or on the watchlist. For technicals/price/momentum questions ONLY. "
                "Do NOT use this for 'do we own/hold X' or 'do we have a position in X' "
                "questions -- use get_position for those instead, since this tool says "
                "nothing about whether the account actually holds the stock."
            ),
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "Stock ticker, e.g. AAPL"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_position",
            "description": (
                "The correct tool for 'do we own/hold X', 'do we have a position in X', "
                "or 'are we in X' questions. Checks whether there's a currently open "
                "position in a specific stock symbol, and its entry price, current "
                "price, and P/L if so."
            ),
            "parameters": {
                "type": "object",
                "properties": {"symbol": {"type": "string", "description": "Stock ticker, e.g. AAPL"}},
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trade_history",
            "description": (
                "Look up completed (closed) trades, most recent first, optionally filtered "
                "to one symbol. Use for questions like 'how did the PANW trade go' or "
                "'what were the last few trades'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Optional ticker to filter by. Omit for all symbols."},
                    "limit": {"type": "integer", "description": "Max trades to return, default 5"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_strategy_settings",
            "description": (
                "Get Cortex's actual current trading strategy configuration: entry score "
                "threshold, stop-loss/take-profit logic, position sizing limits, max "
                "concurrent positions, daily loss limit, extended-hours setting. Use for "
                "any question about strategy, risk rules, or why it would/wouldn't trade something."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_session",
            "description": "Get the precise current market session: REGULAR, PRE_MARKET, AFTER_HOURS, or CLOSED.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_scanner_candidates",
            "description": "Get the current top-ranked stocks from Cortex's watchlist scan, sorted by technical score. Use for 'what are you watching' or 'what looks good right now'.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "How many to return, default 5"}},
                "required": [],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_stock_analysis": _tool_get_stock_analysis,
    "get_position": _tool_get_position,
    "get_trade_history": _tool_get_trade_history,
    "get_strategy_settings": _tool_get_strategy_settings,
    "get_market_session": _tool_get_market_session,
    "get_top_scanner_candidates": _tool_get_top_scanner_candidates,
}

MAX_TOOL_ROUNDS = 5


def ask_cortex_ollama(user_message, alpaca_context=None, model="hermes3:latest", history=None):
    """history: optional list of prior {"role": "user"|"assistant", "content": ...}
    turns for this conversation, oldest first, so Cortex has actual short-term
    memory of the exchange instead of answering each message from scratch."""

    if alpaca_context is None:
        alpaca_context = get_alpaca_context()

    messages = [{"role": "system", "content": CORTEX_SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({
        "role": "user",
        "content": (
            f"{get_time_context()}\n\n"
            f"Live dashboard URL (use this exact link if asked for the Streamlit "
            f"dashboard, web dashboard, or link -- never invent one): {DASHBOARD_URL}\n\n"
            f"Live Alpaca Account Data:\n\n{alpaca_context}\n\n"
            f"Trading Performance History:\n\n{get_learning_context_summary()}\n\n"
            f"Current Strategy/Risk Settings (relay these faithfully, don't invent "
            f"different numbers or mechanisms):\n\n{_tool_get_strategy_settings()}\n\n"
            f"Current Market Session:\n\n{_tool_get_market_session()}\n\n"
            f"User Message:\n{user_message}\n\n"
            "Use the data above when answering questions about the current date/time, "
            "profit, positions, trades, cash, portfolio, performance, dashboard link, "
            "strategy/risk settings, or market session. "
            "For anything more specific -- a stock not shown above, or a particular past "
            "trade -- call the matching tool instead of guessing.\n\n"
            "Answer naturally as Cortex."
        ),
    })

    # Phase 1: let the model fetch whatever live data it needs. Tool-enabled
    # calls are ONLY used to decide whether to fetch something and to gather
    # the results -- their .content is never returned directly (see below).
    for _ in range(MAX_TOOL_ROUNDS):

        response = ollama.chat(model=model, messages=messages, tools=TOOLS)
        msg = response["message"]

        if not msg.tool_calls:
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": msg.tool_calls,
        })

        for call in msg.tool_calls:
            name = call.function.name
            args = call.function.arguments or {}
            func = TOOL_FUNCTIONS.get(name)

            if func is None:
                result = _json.dumps({"error": f"unknown tool '{name}'"})
            else:
                try:
                    result = func(**args)
                except Exception as e:
                    result = _json.dumps({"error": str(e)})

            messages.append({"role": "tool", "content": result})

    # Phase 2: generate the actual reply with `tools` NOT attached. Empirically,
    # merely having tools available (even unused) measurably weakens this
    # model's adherence to other system-prompt instructions -- e.g. it starts
    # confidently answering "who is president" instead of declining, even
    # though the exact same prompt without a tools= param declines correctly.
    # So the tool round(s) above are only ever used to gather data; the final
    # user-facing answer always comes from a clean, tools-free call.
    final = ollama.chat(model=model, messages=messages)
    return final["message"].content
