import os
import discord
import ollama
from discord.ext import commands
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

def get_alpaca_context():

    try:
        alpaca = TradingClient(
            os.getenv("ALPACA_API_KEY"),
            os.getenv("ALPACA_SECRET_KEY"),
            paper=True
        )

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
    await ctx.send(
        """
🤖 CORTEX STATUS

System: ONLINE
Trading: PAPER MODE
AI: Hermes3 ACTIVE
Broker: Alpaca CONNECTED
"""
    )
@bot.command()
async def hello(ctx):
    await ctx.send(
        "Hello! I'm Cortex. Ask me anything or use !positions."
    )
bot.run(TOKEN)