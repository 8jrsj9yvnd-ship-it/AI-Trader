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


bot.run(TOKEN)