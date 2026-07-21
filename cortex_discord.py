import os
import sys
import discord
import ollama
from discord.ext import commands
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from instance_lock import acquire_lock, is_locked

load_dotenv()

if not acquire_lock("cortex_discord"):
    print("Cortex Discord is already running. Exiting.")
    sys.exit(0)

TOKEN = os.getenv("DISCORD_TOKEN")

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
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)
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
        response = ollama.chat(
            model="hermes3:latest",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Cortex, a helpful AI assistant and trading assistant. "
                        "You can answer general questions, explain concepts, help with coding, "
                        "and discuss investing and trading. "
                        "Be concise, accurate, and conversational."
                    ),
                },
                {
                    "role": "user",
"content": f"""
Live Alpaca Account Data:

{get_alpaca_context()}

User Message:
{message.content}

Use the account data above when answering questions about:
- profit
- positions
- trades
- cash
- portfolio
- performance

Answer naturally as Cortex.
"""
                },
            ],
        )

        reply = response["message"]["content"]

        if len(reply) > 1900:
            for i in range(0, len(reply), 1900):
                await message.channel.send(reply[i:i + 1900])
        else:
            await message.channel.send(reply)

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
bot.run(TOKEN)