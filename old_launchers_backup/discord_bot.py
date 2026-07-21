import discord
from discord.ext import commands
import subprocess
import os
from dotenv import load_dotenv
from cortex_brain import ask_cortex
from portfolio import get_trades

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

PYTHON = os.path.join("venv", "Scripts", "python.exe")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Cortex online as {bot.user}")


@bot.command()
async def status(ctx):
    await ctx.send("Running Cortex status check...")

    result = subprocess.run(
        [PYTHON, "autonomous_controller.py"],
        capture_output=True,
        text=True
    )

    response = result.stdout + result.stderr

    if not response:
        response = "No output returned from Cortex."

    await ctx.send(f"```{response[-1900:]}```")


@bot.command()
async def scan(ctx):
    await ctx.send("Running market scan...")

    result = subprocess.run(
        [PYTHON, "ranked_scanner.py"],
        capture_output=True,
        text=True
    )

    response = result.stdout + result.stderr

    if not response:
        response = "No scan output returned."

    await ctx.send(f"```{response[-1900:]}```")


@bot.command()
async def trades(ctx):
    report = get_trades()

    await ctx.send(f"```{report[:1900]}```")


@bot.command()
async def ask(ctx, *, message):
    await ctx.send("Cortex is thinking...")

    response = ask_cortex(message)

    await ctx.send(response[:1900])


@bot.command()
async def commands(ctx):
    message = """
CORTEX COMMANDS
================

!scan
Runs the market scanner

!status
Checks Cortex trader status

!trades
Shows what Cortex bought and current profit/loss

!ask [question]
Talk to Cortex AI

Examples:

!ask What stocks are you watching?

!ask Why did you buy this?

!ask What is my current risk?

!ask Give me today's market summary

"""
    await ctx.send(f"```{message}```")


bot.run(TOKEN)