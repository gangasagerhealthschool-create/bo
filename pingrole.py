import discord
from discord.ext import commands
from discord import app_commands

PINGABLE_ROLES = ["Quickdrop Ping", "Giveaway Ping", "Server Booster"]

class PingRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Ping a specific alert role")
    @app_commands.describe(role="The role to ping")
    async def ping(self, interaction: discord.Interaction, role: str):
        if role not in PINGABLE_ROLES:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid role selected.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

        role_obj = discord.utils.get(interaction.guild.roles, name=role)
        if not role_obj:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Could not find the **{role}** role.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

        # Custom messages for each role
        if role == "Quickdrop Ping":
            content = (
                f"{role_obj.mention} Join up quick! "
                f"{interaction.user.mention} is hosting a quickdrop! 🤑"
            )
        elif role == "Giveaway Ping":
            content = (
                f"{role_obj.mention} Make sure to join! "
                f"W {interaction.user.mention} for hosting a giveaway! 🎉"
            )
            
        elif role == "Server Booster":
            content = (
            	f"{role_obj.mention} Special giveaway! "
                f"W {interaction.user.mention} for hosting a booster quickdrop! 🎉"
            )

        await interaction.response.send_message(
            content=content,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

    @ping.autocomplete('role')
    async def ping_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=r, value=r)
            for r in PINGABLE_ROLES if r.lower().startswith(current.lower())
        ]

async def setup(bot: commands.Bot):
    await bot.add_cog(PingRole(bot))
