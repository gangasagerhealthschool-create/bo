import discord
from discord.ext import commands
from discord import app_commands

class MemberCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="membercount", description="Shows the number of members in the server.")
    async def membercount(self, interaction: discord.Interaction):
        guild = interaction.guild
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans

        embed = discord.Embed(title="📊 Member Count", color=discord.Color.blue())
        embed.add_field(name="Total Members", value=str(total_members), inline=False)
        embed.add_field(name="Humans", value=str(humans), inline=True)
        embed.add_field(name="Bots", value=str(bots), inline=True)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text=f"Server: {guild.name}", icon_url=guild.icon.url if guild.icon else discord.Embed.Empty)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(MemberCount(bot))
