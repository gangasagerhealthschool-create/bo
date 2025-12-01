import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_invite_file(self, guild_id: int) -> str:
        return f"invites_{guild_id}.json"

    def load_invite_data(self, guild_id: int):
        file = self.get_invite_file(guild_id)
        if os.path.exists(file):
            with open(file, "r") as f:
                return {int(k): v for k, v in json.load(f).items()}
        return {}

    def save_invite_data(self, guild_id: int, data: dict):
        file = self.get_invite_file(guild_id)
        with open(file, "w") as f:
            json.dump(data, f)

    @app_commands.command(name="claim_add", description="Add claims to a user")
    @app_commands.describe(user="Select the user", number="Number of claims to add")
    async def invite_add(self, interaction: discord.Interaction, user: discord.Member, number: int):
        guild_id = interaction.guild.id
        invite_data = self.load_invite_data(guild_id)
        invite_data[user.id] = invite_data.get(user.id, 0) + number
        self.save_invite_data(guild_id, invite_data)

        embed = discord.Embed(
            title="✅ Claims Added",
            description=f"{number} claimed invites added to {user.mention}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Claims", value=str(invite_data[user.id]), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claim_remove", description="Remove claims from a user")
    @app_commands.describe(user="Select the user", number="Number of claims to remove")
    async def invite_remove(self, interaction: discord.Interaction, user: discord.Member, number: int):
        guild_id = interaction.guild.id
        invite_data = self.load_invite_data(guild_id)
        invite_data[user.id] = max(0, invite_data.get(user.id, 0) - number)
        self.save_invite_data(guild_id, invite_data)

        embed = discord.Embed(
            title="❌ Claims Removed",
            description=f"{number} claimed invites removed from {user.mention}.",
            color=discord.Color.red()
        )
        embed.add_field(name="Remaining claims", value=str(invite_data[user.id]), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claims_check", description="Check how many claimed invites a user has")
    @app_commands.describe(user="Select the user")
    async def invite_check(self, interaction: discord.Interaction, user: discord.Member):
        guild_id = interaction.guild.id
        invite_data = self.load_invite_data(guild_id)
        current = invite_data.get(user.id, 0)

        embed = discord.Embed(
            title="📊 Claim Check",
            description=f"{user.mention} has claimed **{current}** invites.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
