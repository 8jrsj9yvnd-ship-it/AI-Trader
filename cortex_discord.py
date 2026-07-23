import asyncio
import os
import sys
import tempfile
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import time as dtime
from zoneinfo import ZoneInfo

import discord
import pyttsx3
from discord.ext import commands, tasks
from dotenv import load_dotenv
from instance_lock import acquire_lock, is_locked
from cortex_context import alpaca, get_alpaca_context, ask_cortex_ollama, DASHBOARD_URL
from stock_scanner import analyze_stock, stocks as WATCHLIST
from cortex_learning import load_memory, learning_summary
from market_hours import get_session
import config

# See autonomous_controller.py -- redirected stdout/stderr default to full
# block buffering, which can hide output (including errors) from the log
# files for a long time.
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

load_dotenv()

# NOTE: Discord requires E2EE (the DAVE protocol) on every voice call as of
# March 2026, with no opt-out. Sending audio into a call works fine (discord.py
# handles DAVE encryption for us), but no public library currently implements
# DAVE's receive-side decryption, so a bot cannot understand voice sent by
# real users. This bot can therefore speak into voice channels but not listen.

if not acquire_lock("cortex_discord"):
    print("Cortex Discord is already running. Exiting.")
    sys.exit(0)

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

voice_sessions = {}  # guild_id -> VoiceSession
tts_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cortex-tts")

# Per-channel short-term conversation memory, in-memory only (cleared on
# restart -- not persisted to disk). Capped so the prompt sent to Ollama
# doesn't grow unbounded over a long-running conversation.
HISTORY_TURNS = 10
conversation_history = defaultdict(lambda: deque(maxlen=HISTORY_TURNS * 2))

# Only one guild/channel this bot has ever been added to (verified via the
# Discord API 2026-07-23) -- hardcoded rather than auto-detected each run so
# a future second server doesn't silently redirect the daily post.
GUILD_ID = 1358303268387946606
DAILY_DASHBOARD_CHANNEL_ID = 1358303268387946609
DAILY_DASHBOARD_POST_TIME = dtime(hour=17, minute=0, tzinfo=ZoneInfo("America/Los_Angeles"))


@tasks.loop(time=DAILY_DASHBOARD_POST_TIME)
async def post_daily_dashboard_link():
    channel = bot.get_channel(DAILY_DASHBOARD_CHANNEL_ID)
    if channel is None:
        print(f"[daily dashboard link] channel {DAILY_DASHBOARD_CHANNEL_ID} not found, skipping")
        return
    await channel.send(f"\U0001F4CA **Cortex Dashboard:** {DASHBOARD_URL}")


@bot.event
async def on_ready():
    print(f"Cortex Discord Online: {bot.user}")
    if not post_daily_dashboard_link.is_running():
        post_daily_dashboard_link.start()

    # Guild-scoped sync (not global) so slash commands show up immediately
    # instead of waiting up to an hour for Discord's global propagation.
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} slash commands to guild {GUILD_ID}")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    await message.channel.typing()

    channel_key = message.channel.id
    history = list(conversation_history[channel_key])

    try:
        reply = await asyncio.to_thread(ask_cortex_ollama, message.content, None, "hermes3:latest", history)

        conversation_history[channel_key].append({"role": "user", "content": message.content})
        conversation_history[channel_key].append({"role": "assistant", "content": reply})

        if len(reply) > 1900:
            for i in range(0, len(reply), 1900):
                await message.channel.send(reply[i:i + 1900])
        else:
            await message.channel.send(reply)

        session = voice_sessions.get(message.guild.id) if message.guild else None
        if session is not None:
            await speak_in_session(session, reply)

    except Exception as e:
        await message.channel.send(f"⚠️ Cortex error: {e}")
@bot.hybrid_command(description="Engine/market status and account snapshot")
async def status(ctx):

    engine_state = "🟢 ONLINE" if is_locked("autonomous_controller") else "🔴 OFFLINE"

    try:
        clock = alpaca.get_clock()
        market_state = "OPEN" if clock.is_open else "CLOSED"

        account = alpaca.get_account()
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        day_pl = equity - last_equity
        day_pl_pct = (day_pl / last_equity * 100) if last_equity else 0

        positions = alpaca.get_all_positions()

    except Exception as e:
        await ctx.send(f"⚠️ Cortex error fetching account data: {e}")
        return

    lines = [
        "🤖 **CORTEX STATUS**",
        "",
        f"Engine: {engine_state}",
        f"Market: {market_state}",
        "Trading: PAPER MODE",
        "",
        f"**Equity:** ${equity:,.2f}",
        f"**Day P/L:** ${day_pl:,.2f} ({day_pl_pct:+.2f}%)",
        f"**Cash:** ${float(account.cash):,.2f}",
        f"**Buying Power:** ${float(account.buying_power):,.2f}",
        "",
        f"**Open Positions:** {len(positions)}",
    ]

    await ctx.send("\n".join(lines))


@bot.hybrid_command(description="Show all currently open positions")
async def positions(ctx):

    try:
        positions = alpaca.get_all_positions()
    except Exception as e:
        await ctx.send(f"⚠️ Cortex error fetching positions: {e}")
        return

    if not positions:
        await ctx.send("📊 No open positions.")
        return

    lines = ["📊 **OPEN POSITIONS**", ""]

    for p in positions:
        entry = float(p.avg_entry_price)
        current = float(p.current_price)
        pl_pct = (current - entry) / entry * 100
        arrow = "🟢" if pl_pct >= 0 else "🔴"

        lines.append(
            f"{arrow} **{p.symbol}** — {p.qty} sh @ ${entry:.2f} → ${current:.2f} "
            f"({pl_pct:+.2f}%, ${float(p.unrealized_pl):,.2f})"
        )

    await ctx.send("\n".join(lines))


@bot.hybrid_command(description="Say hi to Cortex")
async def hello(ctx):
    await ctx.send(
        "Hello! I'm Cortex. Ask me anything in plain English, or use !help to see "
        "the fast commands."
    )


@bot.hybrid_command(description="Live price, RSI, and Cortex's technical score for any stock ticker")
@discord.app_commands.describe(symbol="Stock ticker, e.g. AAPL")
async def price(ctx, symbol: str = None):
    if not symbol:
        await ctx.send("Usage: `!price SYMBOL` (e.g. `!price AAPL`)")
        return

    try:
        data = analyze_stock(symbol.upper())
    except Exception as e:
        await ctx.send(f"⚠️ Couldn't analyze {symbol.upper()}: {e}")
        return

    bias_emoji = {"BUY WATCH": "🟢", "NEUTRAL": "🟡", "AVOID": "🔴"}.get(data["bias"], "⚪")

    lines = [
        f"📈 **{data['symbol']}** — ${data['price']}",
        f"{bias_emoji} Score: **{data['score']}/100** ({data['bias']})",
        f"RSI: {data['rsi']} | Volume: {data['volume_strength']}x avg",
        f"1D: {data['day_change']:+.2f}% | 5D: {data['five_day_change']:+.2f}% | 20D: {data['twenty_day_change']:+.2f}%",
    ]
    if data.get("reason"):
        lines.append(f"_{data['reason']}_")

    await ctx.send("\n".join(lines))


@bot.hybrid_command(description="Recent closed trades, optionally filtered to one symbol")
@discord.app_commands.describe(symbol="Optional ticker to filter by, e.g. AAPL")
async def trades(ctx, symbol: str = None):
    memory = load_memory()
    completed = [t for t in memory if "profit_loss" in t]

    if symbol:
        completed = [t for t in completed if t.get("symbol", "").upper() == symbol.upper()]

    completed = list(reversed(completed))[:10]

    if not completed:
        target = f" for {symbol.upper()}" if symbol else ""
        await ctx.send(f"📉 No completed trades recorded{target}.")
        return

    header = f"📉 **RECENT TRADES{' — ' + symbol.upper() if symbol else ''}**"
    lines = [header, ""]

    for t in completed:
        pl = t.get("profit_loss", 0)
        arrow = "🟢" if pl >= 0 else "🔴"
        lines.append(
            f"{arrow} **{t.get('symbol', '?')}** {t.get('date', '')} — "
            f"buy ${t.get('buy_price', 0):.2f} / sell ${t.get('sell_price', 0):.2f} "
            f"→ ${pl:,.2f}"
        )

    await ctx.send("\n".join(lines))


async def _symbol_autocomplete(interaction: discord.Interaction, current: str):
    current = (current or "").upper()
    matches = [s for s in WATCHLIST if s.startswith(current)][:25]
    return [discord.app_commands.Choice(name=s, value=s) for s in matches]


price.autocomplete("symbol")(_symbol_autocomplete)
trades.autocomplete("symbol")(_symbol_autocomplete)


@bot.hybrid_command(description="Win rate and total P/L across completed trades")
async def performance(ctx):
    await ctx.send(f"📊 **PERFORMANCE**\n{learning_summary()}")


@bot.hybrid_command(description="Cortex's current entry/exit/risk settings")
async def strategy(ctx):
    lines = [
        "⚙️ **STRATEGY SETTINGS**",
        "",
        f"Min entry score: **{config.MIN_ENTRY_SCORE}**/100",
        f"Min volume strength: **{config.MIN_VOLUME_STRENGTH}x** avg",
        f"Stop-loss: **{config.ATR_STOP_MULTIPLIER}x ATR** (fallback: flat {config.STOP_LOSS_PERCENT*100:.0f}%)",
        f"Take-profit: **{config.TAKE_PROFIT_RATIO}:1** reward:risk",
        f"Max open positions: **{config.MAX_OPEN_POSITIONS}**",
        f"Max shares/trade: **{config.MAX_SHARES_PER_TRADE}**",
        f"Risk per trade: **{config.RISK_PER_TRADE*100:.1f}%** of equity",
        f"Max daily loss: **{config.MAX_DAILY_LOSS*100:.0f}%** (halts new entries for the day)",
        f"Extended hours: **{'enabled' if config.ENABLE_EXTENDED_HOURS else 'disabled'}**",
    ]
    await ctx.send("\n".join(lines))


@bot.hybrid_command(description="Precise market session: regular, pre-market, after-hours, or closed")
async def session(ctx):
    try:
        s = get_session()
    except Exception as e:
        await ctx.send(f"⚠️ Couldn't determine market session: {e}")
        return
    await ctx.send(f"🕐 Market session: **{s}**")


@bot.hybrid_command(description="Top-ranked watchlist stocks right now")
async def watchlist(ctx):
    results = []
    for sym in WATCHLIST:
        try:
            results.append(analyze_stock(sym))
        except Exception:
            pass
    results.sort(key=lambda x: x["score"], reverse=True)

    lines = ["🔍 **WATCHLIST — top 5 by score**", ""]
    for s in results[:5]:
        bias_emoji = {"BUY WATCH": "🟢", "NEUTRAL": "🟡", "AVOID": "🔴"}.get(s["bias"], "⚪")
        lines.append(f"{bias_emoji} **{s['symbol']}** — {s['score']}/100 (${s['price']}, RSI {s['rsi']})")

    await ctx.send("\n".join(lines))


@bot.hybrid_command(description="List everything Cortex can do")
async def help(ctx):
    lines = [
        "🤖 **CORTEX COMMANDS**",
        "",
        "Just talk to me normally for anything -- ask about a specific stock, "
        "a past trade, why the strategy works a certain way, or general questions. "
        "I remember the last few messages in this channel.",
        "",
        "**Fast commands** (instant, no AI needed):",
        "`!status` — engine/market status + account snapshot",
        "`!positions` — open positions",
        "`!price SYMBOL` — live price/RSI/score for any ticker",
        "`!trades [SYMBOL]` — recent closed trades, optionally filtered",
        "`!performance` — win rate / total P&L",
        "`!strategy` — current entry/exit/risk settings",
        "`!session` — precise market session (regular/pre/after/closed)",
        "`!watchlist` — top-ranked watchlist stocks right now",
        "`!join` / `!leave` / `!say <text>` — voice channel controls",
        "",
        f"📊 Dashboard: {DASHBOARD_URL}",
    ]
    await ctx.send("\n".join(lines))


class VoiceSession:

    def __init__(self, guild, vc, text_channel):
        self.guild = guild
        self.vc = vc
        self.text_channel = text_channel
        self.speaking = asyncio.Lock()


def synthesize_tts(text):
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    engine = pyttsx3.init()
    try:
        engine.save_to_file(text, path)
        engine.runAndWait()
    finally:
        engine.stop()

    return path


async def play_and_wait(vc, path):
    loop = asyncio.get_running_loop()
    done = asyncio.Event()

    def after(error):
        if error:
            print(f"[voice] playback error: {error}")
        loop.call_soon_threadsafe(done.set)

    source = discord.FFmpegPCMAudio(path)
    vc.play(source, after=after)
    await done.wait()


async def speak_in_session(session, text):
    async with session.speaking:
        loop = asyncio.get_running_loop()
        try:
            path = await loop.run_in_executor(tts_executor, synthesize_tts, text)
        except Exception as e:
            await session.text_channel.send(f"⚠️ Cortex voice error (TTS): {e}")
            return

        try:
            await play_and_wait(session.vc, path)
        except Exception as e:
            await session.text_channel.send(f"⚠️ Cortex voice error (playback): {e}")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


async def teardown_session(session):
    try:
        await session.vc.disconnect(force=True)
    except Exception:
        pass


@bot.hybrid_command(description="Join your current voice channel so Cortex can speak replies out loud")
async def join(ctx):
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel first.")
        return

    if ctx.guild.id in voice_sessions:
        await ctx.send("Already in a voice session in this server. Use !leave first.")
        return

    try:
        vc = await ctx.author.voice.channel.connect()
    except Exception as e:
        await ctx.send(f"Could not join voice channel: {e}")
        return

    session = VoiceSession(ctx.guild, vc, ctx.channel)
    voice_sessions[ctx.guild.id] = session

    await ctx.send(
        f"🎙️ Joined {ctx.author.voice.channel.name}. "
        "I can speak here — talk to me in text and I'll answer out loud too, "
        "or use !say <text>."
    )


@bot.hybrid_command(description="Have Cortex speak text out loud in the voice channel it's joined")
@discord.app_commands.describe(text="What Cortex should say")
async def say(ctx, *, text: str):
    session = voice_sessions.get(ctx.guild.id)
    if session is None:
        await ctx.send("I'm not in a voice channel. Use !join first.")
        return

    await speak_in_session(session, text)


@bot.hybrid_command(description="Leave the current voice channel")
async def leave(ctx):
    session = voice_sessions.pop(ctx.guild.id, None)
    if session is None:
        await ctx.send("Not currently in a voice session.")
        return

    await teardown_session(session)
    await ctx.send("👋 Left the voice channel.")


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id != bot.user.id or after.channel is not None:
        return

    session = voice_sessions.pop(member.guild.id, None)
    if session is not None:
        await teardown_session(session)


bot.run(TOKEN)