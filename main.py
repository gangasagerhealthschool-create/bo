import discord
from discord.ext import commands
import asyncio

TOKEN = "bot-token"  # Replace this with your real token

# Set up intents and bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, application_id=)

synced = False

# Event triggered when the bot is ready
@bot.event
async def on_ready():
    global synced
    if not synced:
        await bot.tree.sync()  # GLOBAL SYNC for slash commands
        synced = True
        print("🌍 Synced global commands.")
    print(f"🚀 Bot is ready. Logged in as {bot.user}")

# Load extensions (cogs)
async def load_extensions():
    try:
        # Await load_extension since it's an async method
        await bot.load_extension("cogs.invite_tracker")
        await bot.load_extension("cogs.giveaway")
        await bot.load_extension("cogs.staffroles")
        await bot.load_extension("cogs.split_steal")
        await bot.load_extension("cogs.moderation")
        await bot.load_extension("cogs.LockUnlockCog")  # Now awaiting this call
        await bot.load_extension("cogs.purge")
        await bot.load_extension("cogs.autojoinrole")
        await bot.load_extension("cogs.logs")
        await bot.load_extension("cogs.pingrole")
        await bot.load_extension("cogs.membercount")
    except Exception as e:
        print(f"Error loading extension: {e}")

# Main entry point for running the bot
async def main():
    async with bot:
        await load_extensions()  # Load all cogs/extensions
        await bot.start(TOKEN)   # Start the bot with your token

# Run the bot
asyncio.run(main())
