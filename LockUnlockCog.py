import discord
from discord.ext import commands
from discord import app_commands, Interaction

class LockUnlock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_staff_role(self, guild: discord.Guild) -> discord.Role:
        for role in guild.roles:
            if role.name.lower() == "staff team":
                return role
        return None

    @app_commands.command(name="lock", description="Lock the current channel for non-staff.")
    async def lock(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        guild = interaction.guild
        staff_role = await self._get_staff_role(guild)

        if not staff_role:
            await interaction.followup.send("❌ Couldn't find a role named **Staff Team**.")
            return

        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(guild.default_role, overwrite=overwrite)

        await interaction.followup.send(f"🔒 Locked {channel.mention} for everyone except **{staff_role.name}**.")
        await channel.send("🔒 This channel has been locked by staff.")

    @app_commands.command(name="unlock", description="Unlock the current channel for everyone.")
    async def unlock(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        guild = interaction.guild

        overwrite = channel.overwrites_for(guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(guild.default_role, overwrite=overwrite)

        await interaction.followup.send(f"🔓 Unlocked {channel.mention}.")
        await channel.send("🔓 This channel has been unlocked by staff.")

# Cog setup function
async def setup(bot):
    await bot.add_cog(LockUnlock(bot))  # This is the correct way, no need to await