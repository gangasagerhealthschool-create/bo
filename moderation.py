import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import utcnow
from datetime import timedelta
import json
import os
import re

def parse_duration(duration_str):
    pattern = r'((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?'
    match = re.fullmatch(pattern, duration_str)
    if not match:
        raise ValueError("Invalid duration format. Use '1d2h30m'.")
    time_params = {k: int(v) for k, v in match.groupdict(default='0').items()}
    return timedelta(**time_params)

def get_moderation_log_channel(guild: discord.Guild):
    path = f"server_data/{guild.id}_settings.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        data = json.load(f)
    return guild.get_channel(data.get("modlog_channel"))

MUTE_REASONS = [
    app_commands.Choice(name='Spamming', value='spamming'),
    app_commands.Choice(name='Toxicity', value='toxicity'),
    app_commands.Choice(name='Racism', value='racism'),
    app_commands.Choice(name='Threatening', value='threatening'),
    app_commands.Choice(name='Advertising', value='advertising'),
]

BAN_REASONS = [
    app_commands.Choice(name='Ban Evading', value='ban_evading'),
    app_commands.Choice(name='Doxxing', value='doxxing'),
    app_commands.Choice(name='DDoS Attack', value='ddos_attack'),
    app_commands.Choice(name='Inappropriate Profile', value='inappropriate_profile'),
    app_commands.Choice(name='NSFW', value='nsfw'),
]

MUTE_DURATIONS = {
    'spamming': timedelta(minutes=15),
    'racism': timedelta(days=3),
    'toxicity': timedelta(minutes=30),
    'threatening': timedelta(days=7),
    'advertising': timedelta(days=1),
}

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, interaction, title, user, reason, proof=None):
        channel = get_moderation_log_channel(interaction.guild)
        if not channel:
            return
        embed = discord.Embed(title=title, color=discord.Color.red())
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else discord.Embed.Empty)
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if proof:
            embed.set_image(url=proof.url)
        await channel.send(embed=embed)

    @app_commands.command(name="mute", description="Mute a specific member")
    @app_commands.describe(member='Member to mute', reason='Reason for mute', proof='Proof attachment')
    @app_commands.choices(reason=MUTE_REASONS)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: app_commands.Choice[str], proof: discord.Attachment):
        duration = MUTE_DURATIONS.get(reason.value)
        if not duration:
            await interaction.response.send_message("No duration configured for this reason.", ephemeral=True)
            return

        if member.top_role > interaction.user.top_role:
            await interaction.response.send_message(
                "You can't moderate members with higher roles than yours.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't mute this member because their top role is higher or equal to mine.", ephemeral=True
            )
            return

        try:
            await member.edit(timed_out_until=utcnow() + duration, reason=reason.name)
        except Exception as e:
            await interaction.response.send_message(f"Failed to mute member: {e}", ephemeral=True)
            return

        await self.send_log(interaction, "🔇 Member Timed Out", member, reason.name, proof)
        await interaction.response.send_message(f"✅ {member.mention} has been muted for {str(duration)} due to **{reason.name}**.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a specific user")
    @app_commands.describe(user='User to ban', reason='Reason for ban', proof='Proof attachment')
    @app_commands.choices(reason=BAN_REASONS)
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: app_commands.Choice[str], proof: discord.Attachment):
        member = interaction.guild.get_member(user.id)
        if member:
            if member.top_role > interaction.user.top_role:
                await interaction.response.send_message(
                    "You can't ban members with higher roles than yours.", ephemeral=True
                )
                return

            if member.top_role >= interaction.guild.me.top_role:
                await interaction.response.send_message(
                    "I can't ban this member because their top role is higher or equal to mine.", ephemeral=True
                )
                return

        try:
            await interaction.guild.ban(user, reason=reason.name)
        except Exception as e:
            await interaction.response.send_message(f"Failed to ban user: {e}", ephemeral=True)
            return

        await self.send_log(interaction, "🔨 Member Banned", user, reason.name, proof)
        await interaction.response.send_message(f"✅ {user.mention} has been banned for **{reason.name}**.", ephemeral=True)

    @app_commands.command(name="unmute", description="Unmute a member currently muted")
    @app_commands.describe(member="Member to unmute", reason="Reason for unmute")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if not member.timed_out_until or member.timed_out_until < utcnow():
            await interaction.response.send_message("This member is not currently muted.", ephemeral=True)
            return

        if member.top_role > interaction.user.top_role:
            await interaction.response.send_message(
                "You can't unmute members with higher roles than yours.", ephemeral=True
            )
            return

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't unmute this member because their top role is higher or equal to mine.", ephemeral=True
            )
            return

        try:
            await member.edit(timed_out_until=None, reason=reason)
        except Exception as e:
            await interaction.response.send_message(f"Failed to unmute member: {e}", ephemeral=True)
            return

        await self.send_log(interaction, "🔊 Member Unmuted", member, reason)
        await interaction.response.send_message(f"✅ {member.mention} has been unmuted.", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.describe(user="User to unban", reason="Reason for unban")
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str):
        try:
            bans = await interaction.guild.bans()
            if discord.utils.find(lambda b: b.user.id == user.id, bans):
                await interaction.guild.unban(user, reason=reason)
            else:
                await interaction.response.send_message("❌ This user is not banned.", ephemeral=True)
                return
        except Exception as e:
            await interaction.response.send_message(f"Failed to unban user: {e}", ephemeral=True)
            return

        await self.send_log(interaction, "♻️ Member Unbanned", user, reason)
        await interaction.response.send_message(f"✅ {user.mention} has been unbanned.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
