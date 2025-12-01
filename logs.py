import discord
from discord.ext import commands
from discord import app_commands, Interaction
import json
import os

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="logs", description="Set the log channel for moderation, welcome, staff, tickets")
    @app_commands.describe(
        type="The type of log to set (moderation, welcome, staff, giveaway)",
        channel="The channel where logs should be sent"
    )
    async def logs(
        self,
        interaction: Interaction,
        type: str,
        channel: discord.TextChannel
    ):
        log_types = {
            "moderation": "modlog_channel",
            "welcome": "welcome_channel",
            "staff": "stafflog_channel",
            "ticket": "giveaway_log"
        }

        type = type.lower()
        if type not in log_types:
            await interaction.response.send_message(
                "❌ Invalid type. Choose from: moderation, welcome, staff, ticket.",
                ephemeral=True
            )
            return

        file_path = f"server_data/{interaction.guild.id}_settings.json"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
        else:
            data = {}

        data[log_types[type]] = channel.id

        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

        await interaction.response.send_message(
            f"✅ {type.capitalize()} log channel set to {channel.mention}.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Logs(bot))
