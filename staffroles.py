import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class StaffUpdate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="staffupdate",
        description="Promote or demote a staff member"
    )
    @app_commands.describe(
        member="The staff member to update",
        new_role="The new role to assign (choose from hierarchy)"
    )
    async def staffupdate(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        new_role: str
    ):
        await interaction.response.defer(ephemeral=True)

        # 1) define hierarchy and resolve role object
        hierarchy = [
            "Member", "Trainee", "Helper", "Moderator",
            "Sr Moderator", "Administrator", "Sr Administrator", "Developer", "Management", "Executive", "Co Owner", "Owner"
        ]
        role_obj = discord.utils.get(interaction.guild.roles, name=new_role)
        if not role_obj or role_obj.name not in hierarchy:
            return await interaction.followup.send(
                f"⚠️ `{new_role}` is not in the staff hierarchy.",
                ephemeral=True
            )

        # 2) load role data
        gid = str(interaction.guild.id)
        path = f"staffroledata_{gid}.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
        else:
            data = {}

        # Default old name if not stored
        old_name = data.get(str(member.id), "Member")
        old_idx = hierarchy.index(old_name)
        new_idx = hierarchy.index(new_role)

        # Get invoker's staff level
        invoker_id = str(interaction.user.id)
        invoker_name = data.get(invoker_id, "Member")
        invoker_idx = hierarchy.index(invoker_name)

        # Protection checks
        if member.id == interaction.user.id:
            return await interaction.followup.send(
                "❌ You cannot promote or demote yourself.",
                ephemeral=True
            )

        if old_idx >= invoker_idx and interaction.user.id != interaction.guild.owner_id:
            return await interaction.followup.send(
                f"❌ You cannot modify {member.mention} because their current rank (`{old_name}`) is equal to or higher than yours (`{invoker_name}`).",
                ephemeral=True
            )

        if new_idx >= invoker_idx and interaction.user.id != interaction.guild.owner_id:
            return await interaction.followup.send(
                f"❌ You cannot assign the role `{new_role}` because it's equal to or higher than your own rank (`{invoker_name}`).",
                ephemeral=True
            )

        if old_name == new_role:
            return await interaction.followup.send(
                f"⚠️ {member.mention} already has the role `{new_role}`.",
                ephemeral=True
            )

        # Update data
        data[str(member.id)] = new_role
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

        # 3) build embed
        is_promo = new_idx > old_idx
        title = (
            "<:arrowup:1398792098857357462> Staff Promotion <:arrowup:1398792098857357462>"
            if is_promo else
            "<:arrowdown:1398791955588186152> Staff Demotion <:arrowdown:1398791955588186152>"
        )
        action = "PROMOTED to" if is_promo else "DEMOTED to"
        by = "Promoted By" if is_promo else "Demoted By"

        embed = discord.Embed(
            title=title,
            description=(
                f"{member.mention} **Has Been {action}** {role_obj.mention}\n"
                f"-# {by}: {interaction.user.mention}"
            ),
            color=discord.Color.green() if is_promo else discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(
            text=f"Updated by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )
        embed.timestamp = discord.utils.utcnow()

        # 4) compute role changes
        member_role     = discord.utils.get(interaction.guild.roles, name="Member")
        staff_team_role = discord.utils.get(interaction.guild.roles, name="Staff Team")

        to_remove = [
            r for r in member.roles
            if (r.name in hierarchy and r.name != "Member" and r.name != new_role)
        ]
        if new_role == "Member" and staff_team_role in member.roles:
            to_remove.append(staff_team_role)

        to_add = []
        if member_role and member_role not in member.roles:
            to_add.append(member_role)
        if role_obj not in member.roles:
            to_add.append(role_obj)

        # Apply role changes
        if to_remove:
            await member.remove_roles(*to_remove, reason="StaffUpdate cleanup")
        if to_add:
            await member.add_roles(*to_add, reason="StaffUpdate assignment")

        # 5) log in stafflog channel
        cfg = f"server_data/{interaction.guild.id}_settings.json"
        if os.path.exists(cfg):
            with open(cfg, "r") as f:
                settings = json.load(f)
            ch_id = settings.get("stafflog_channel")
            if ch_id:
                ch = interaction.guild.get_channel(ch_id)
                if ch:
                    await ch.send(embed=embed)

        # 6) DM with plain role name instead of mention
        dm_embed = embed.copy()
        dm_embed.description = (
            f"You have been **{action.lower()}** to **{role_obj.name}**\n"
            f"-# {by}: {interaction.user}"
        )
        try:
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await interaction.followup.send(
            "✅ Staff update recorded and logged.",
            ephemeral=True
        )

    @staffupdate.autocomplete('new_role')
    async def staffupdate_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        hierarchy = {
            "Member", "Trainee", "Helper", "Moderator",
            "Sr Moderator", "Administrator", "Sr Administrator", "Developer", "Management", "Executive", "Co Owner", "Owner"
        }
        choices = [
            app_commands.Choice(name=r.name, value=r.name)
            for r in interaction.guild.roles
            if r.name in hierarchy and current.lower() in r.name.lower()
        ]
        return choices

async def setup(bot: commands.Bot):
    await bot.add_cog(StaffUpdate(bot))
