import asyncio
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import discord
import pyttsx3
from discord.ext import commands
from dotenv import load_dotenv
from instance_lock import acquire_lock, is_locked
from cortex_context import alpaca, get_alpaca_context, ask_cortex_ollama

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


@bot.event
async def on_ready():
    print(f"Cortex Discord Online: {bot.user}")


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    await message.channel.typing()

    try:
        reply = await asyncio.to_thread(ask_cortex_ollama, message.content)

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
@bot.command()
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


@bot.command()
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


@bot.command()
async def hello(ctx):
    await ctx.send(
        "Hello! I'm Cortex. Ask me anything, or use !status / !positions."
    )


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


@bot.command()
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


@bot.command()
async def say(ctx, *, text: str):
    session = voice_sessions.get(ctx.guild.id)
    if session is None:
        await ctx.send("I'm not in a voice channel. Use !join first.")
        return

    await speak_in_session(session, text)


@bot.command()
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