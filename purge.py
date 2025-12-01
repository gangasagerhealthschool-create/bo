import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import json
import os

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_moderation_log_channel(self, guild: discord.Guild):
        path = f"server_data/{guild.id}_settings.json"
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
                log_channel_id = data.get("modlog_channel")
                if log_channel_id:
                    return guild.get_channel(log_channel_id)
        except Exception as e:
            print(f"[ERROR] Failed to load moderation log channel: {e}")
        return None

    @app_commands.command(name="purge", description="Delete a number of messages from the channel.")
    @app_commands.describe(amount="Number of messages to delete (max 100)")
    async def purge(self, interaction: discord.Interaction, amount: int):
        print(f"[DEBUG] /purge command invoked with amount {amount} by {interaction.user}")

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(":x: You don't have permission to manage messages.", ephemeral=True)
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message("⚠ You can only purge between 1 and 100 messages.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        cutoff = interaction.created_at - timedelta(seconds=1)

        def is_eligible(msg: discord.Message):
            return msg.created_at < cutoff

        try:
            purged = await interaction.channel.purge(limit=amount + 1, check=is_eligible)
            purged = purged[:amount]
        except Exception as e:
            print(f"[ERROR] Error while purging messages: {e}")
            await interaction.followup.send(":x: Failed to purge messages.", ephemeral=True)
            return

        if not purged:
            await interaction.followup.send(":x: No messages found to purge.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🧹 Messages Purged",
            description=f"**{len(purged)}** messages were purged by {interaction.user.mention} in {interaction.channel.mention}.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        log_channel = await self.get_moderation_log_channel(interaction.guild)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
                print("[DEBUG] Purge log sent to moderation log channel.")
            except Exception as e:
                print(f"[ERROR] Failed to send embed to log channel: {e}")
        else:
            print("[DEBUG] No moderation log channel set.")

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Purge(bot))
    print("[DEBUG] Purge cog loaded successfully.")
