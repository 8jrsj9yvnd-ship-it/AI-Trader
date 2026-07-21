import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():

    print(
        f"Cortex Discord Online: {bot.user}"
    )


@bot.command()
async def cortex(ctx):

    await ctx.send(
        """
🧠 CORTEX ONLINE

System:
ONLINE

Trading Engine:
READY

Mode:
PAPER TRADING

"""
    )


@bot.command()
async def hello(ctx):

    await ctx.send(
        "Cortex is awake."
    )
@bot.command()
async def status(ctx):

    await ctx.send(
        """
🤖 CORTEX STATUS

System:
ONLINE

Trading:
PAPER MODE

AI:
Hermes3 ACTIVE

Broker:
Alpaca CONNECTED
"""
    )


@bot.command()
async def positions(ctx):

    from alpaca.trading.client import TradingClient
    import os

    alpaca = TradingClient(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        paper=True
    )

    positions = alpaca.get_all_positions()

    if not positions:
        await ctx.send("No open positions.")
        return


    message = "📈 CORTEX POSITIONS\n\n"

    for p in positions:

        message += (
            f"{p.symbol}\n"
            f"Shares: {p.qty}\n"
            f"P/L: ${p.unrealized_pl}\n\n"
        )


    await ctx.send(message)

bot.run(TOKEN)