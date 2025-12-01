import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta, timezone

class AutoJoinRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    def get_settings_path(self, guild_id):
        os.makedirs("server_data", exist_ok=True)
        return f"server_data/{guild_id}_settings.json"

    def get_invite_data_path(self, guild_id):
        os.makedirs("server_data", exist_ok=True)
        return f"server_data/{guild_id}_invites.json"

    def get_members_data_path(self, guild_id):
        os.makedirs("server_data", exist_ok=True)
        return f"server_data/{guild_id}_members.json"

    def save_setting(self, guild_id, key, value):
        path = self.get_settings_path(guild_id)
        data = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        data[key] = value
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def load_setting(self, guild_id, key):
        path = self.get_settings_path(guild_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    data = json.load(f)
                    return data.get(key)
                except json.JSONDecodeError:
                    return None
        return None

    def load_invite_counts(self, guild_id):
        path = self.get_invite_data_path(guild_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_invite_counts(self, guild_id, data):
        path = self.get_invite_data_path(guild_id)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def load_members_data(self, guild_id):
        path = self.get_members_data_path(guild_id)
        if os.path.exists(path):
            with open(path, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_members_data(self, guild_id, data):
        path = self.get_members_data_path(guild_id)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    @app_commands.command(name="join_role", description="Set a role to automatically give when someone joins")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def join_role(self, interaction: discord.Interaction, role: discord.Role):
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("That role is higher than my top role. Please choose a lower role.", ephemeral=True)
            return

        self.save_setting(interaction.guild.id, "join_role", role.id)
        await interaction.response.send_message(f"✅ Members who join will now receive the **{role.name}** role.", ephemeral=True)

    @app_commands.command(name="invites", description="Check how many people a user has invited")
    async def invites(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        invite_data = self.load_invite_counts(interaction.guild.id)
        joined = invite_data.get(str(user.id), {}).get("joined", 0)
        left = invite_data.get(str(user.id), {}).get("left", 0)
        fake = invite_data.get(str(user.id), {}).get("fake", 0)
        net_invites = joined - left - fake

        embed = discord.Embed(
            title=f"Invite Stats for {user.name}",
            description=(
                f"**Joined:** {joined}\n"
                f"**Left:** {left}\n"
                f"**Fake Invites (accounts < 7 days):** {fake}\n"
                f"**Net Invites:** {net_invites}"
            ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite_leaderboard", description="See the top inviters in the server.")
    async def invite_leaderboard(self, interaction: discord.Interaction):
        invite_data = self.load_invite_counts(interaction.guild.id)
        leaderboard = []

        for user_id, stats in invite_data.items():
            joined = stats.get("joined", 0)
            left = stats.get("left", 0)
            net = joined - left
            leaderboard.append((user_id, joined, left, net))

        leaderboard.sort(key=lambda x: x[3], reverse=True)
        top_entries = leaderboard[:10]

        description = ""
        for i, (user_id, joined, left, net) in enumerate(top_entries, start=1):
            user = interaction.guild.get_member(int(user_id))
            name = user.mention if user else f"<@{user_id}>"
            description += f"**{i}.** {name} → **{net}** (joined: {joined}, left: {left})\n"

        if not description:
            description = "No invite data found."

        embed = discord.Embed(
            title="🏆 Invite Leaderboard",
            description=description,
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invitesreset", description="Reset invite counts. Leave empty to reset all, or mention a user to reset one.")
    @app_commands.describe(user="(Optional) The user whose invites to reset.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def invitesreset(self, interaction: discord.Interaction, user: discord.User = None):
        guild_id = interaction.guild.id
        invite_data = self.load_invite_counts(guild_id)
        claims_path = f"invites_{guild_id}.json"

        if user is None:
            for uid in invite_data:
                invite_data[uid] = {"joined": 0, "left": 0, "fake": 0}
            self.save_invite_counts(guild_id, invite_data)

            if os.path.exists(claims_path):
                with open(claims_path, "w") as f:
                    json.dump({}, f, indent=4)

            await interaction.response.send_message("✅ All invite stats and claims have been reset.", ephemeral=True)
        else:
            uid = str(user.id)
            if uid in invite_data:
                invite_data[uid] = {"joined": 0, "left": 0, "fake": 0}
                self.save_invite_counts(guild_id, invite_data)

            if os.path.exists(claims_path):
                try:
                    with open(claims_path, "r") as f:
                        claims = json.load(f)
                    if uid in claims:
                        del claims[uid]
                        with open(claims_path, "w") as f:
                            json.dump(claims, f, indent=4)
                except json.JSONDecodeError:
                    pass

            await interaction.response.send_message(f"✅ Invite stats and claims reset for {user.mention}.", ephemeral=True)

    async def update_invites(self, guild: discord.Guild):
        try:
            self.invites[guild.id] = await guild.invites()
        except discord.Forbidden:
            self.invites[guild.id] = []

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.update_invites(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.update_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.update_invites(invite.guild)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.update_invites(invite.guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        inviter = "Unknown"
        inviter_id = None

        try:
            before = self.invites.get(guild.id, [])
            after = await guild.invites()
            for old in before:
                for new in after:
                    if old.code == new.code and new.uses > old.uses:
                        inviter = new.inviter.mention
                        inviter_id = new.inviter.id
                        break
        except Exception as e:
            print(f"Error checking invites: {e}")

        await self.update_invites(guild)

        members_data = self.load_members_data(guild.id)
        invite_data = self.load_invite_counts(guild.id)

        now = datetime.now(timezone.utc)
        account_age = now - member.created_at
        is_fake = account_age < timedelta(days=7)  # Account younger than 3 days = fake invite

        if inviter_id and str(member.id) not in members_data:
            if str(inviter_id) not in invite_data:
                invite_data[str(inviter_id)] = {"joined": 0, "left": 0, "fake": 0}

            if is_fake:
                invite_data[str(inviter_id)]["fake"] = invite_data[str(inviter_id)].get("fake", 0) + 1
            else:
                invite_data[str(inviter_id)]["joined"] += 1

            members_data[str(member.id)] = {"inviter_id": inviter_id, "fake": is_fake}
            self.save_invite_counts(guild.id, invite_data)

        role_id = self.load_setting(guild.id, "join_role")
        role = guild.get_role(role_id) if role_id else None
        if role:
            try:
                await member.add_roles(role, reason="Auto-assigned join role")
            except discord.Forbidden:
                print(f"Missing permissions to assign role {role.name} in {guild.name}")
            members_data[str(member.id)]["role"] = role.name

        self.save_members_data(guild.id, members_data)

        channel_id = self.load_setting(guild.id, "welcome_channel")
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                description = f"Welcome to **{guild.name}**, {member.mention}!\nInvited by: {inviter}"
                if is_fake:
                    description += "\n⚠️ Account is new (< 3 days old) — counted as a fake invite."
                embed = discord.Embed(
                    title="🎉 Welcome!",
                    description=description,
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                embed.set_footer(text=f"Member #{len(guild.members)}")
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    print(f"Missing permissions to send welcome message in {channel.name}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        members_data = self.load_members_data(guild.id)
        invite_data = self.load_invite_counts(guild.id)

        member_info = members_data.pop(str(member.id), None)
        if member_info and "inviter_id" in member_info:
            inviter_id = member_info["inviter_id"]
            if str(inviter_id) not in invite_data:
                invite_data[str(inviter_id)] = {"joined": 0, "left": 0, "fake": 0}
            invite_data[str(inviter_id)]["left"] += 1
            self.save_invite_counts(guild.id, invite_data)

        self.save_members_data(guild.id, members_data)

async def setup(bot):
    await bot.add_cog(AutoJoinRole(bot))
