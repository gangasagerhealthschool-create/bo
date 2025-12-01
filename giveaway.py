import discord
from discord.ext import commands
from discord import app_commands
import os, json, asyncio, random
from datetime import datetime, timedelta, timezone

# ─── Utilities ─────────────────────────────────────────────────────────────────

def parse_duration(duration: str):
    total = 0
    num = ""
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    for c in duration:
        if c.isdigit():
            num += c
        elif c in units and num:
            total += int(num) * units[c]
            num = ""
        else:
            return None
    return total if total > 0 else None

# ─── Live Giveaway Embed ─────────────────────────────────────────────────────────

def create_giveaway_embed(prize, end_time, host, entries, winners):
    ts = int(end_time.timestamp())
    embed = discord.Embed(
        title=f"{prize}",
        description=(
            f"Hosted by: {host.mention}\n"
            f"Entries: {entries}\n"
            f"Winners: {winners}\n"
            f"Time: <t:{ts}:R>"
        ),
        color=discord.Color.pink()
    )
    return embed

# ─── The “Enter” Button ────────────────────────────────────────────────────────

class GiveawayView(discord.ui.View):
    def __init__(self, cog, giveaway_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.gid = giveaway_id

    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.primary)
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        g = self.cog.giveaways.get(self.gid)
        if not g:
            return await interaction.response.send_message("⚠️ This giveaway has ended.", ephemeral=True)

        uid = interaction.user.id
        if uid in g["entries"]:
            return await interaction.response.send_message("❌ You’ve already entered!", ephemeral=True)

        g["entries"].add(uid)
        self.cog.save_giveaways(interaction.guild.id)
        await interaction.response.send_message("✅ You have entered!", ephemeral=True)

        host_user = interaction.guild.get_member(g["host"]) or self.cog.bot.get_user(g["host"])
        await g["message"].edit(
            embed=create_giveaway_embed(
                g["prize"], g["end_time"], host_user, len(g["entries"]), g["winners"]
            )
        )

# ─── The Modal ─────────────────────────────────────────────────────────────────

class GiveawayModal(discord.ui.Modal, title="Giveaway Setup"):
    duration = discord.ui.TextInput(label="Duration", placeholder="e.g. 1d2h30m", required=True)
    winners = discord.ui.TextInput(label="Number of Winners", placeholder="e.g. 1", required=True)
    prize = discord.ui.TextInput(label="Prize", placeholder="e.g. Nitro, $10", required=True)

    def __init__(self, cog, interaction):
        super().__init__()
        self.cog = cog
        self.interaction = interaction

    async def on_submit(self, interaction: discord.Interaction):
        sec = parse_duration(self.duration.value)
        if sec is None:
            return await interaction.response.send_message("❌ Invalid duration format!", ephemeral=True)

        try:
            win_count = int(self.winners.value)
        except ValueError:
            return await interaction.response.send_message("❌ Number of winners must be a number!", ephemeral=True)

        end_time = datetime.now(timezone.utc) + timedelta(seconds=sec)
        host_id = self.interaction.user.id
        embed = create_giveaway_embed(self.prize.value, end_time, self.interaction.user, 0, win_count)
        view = GiveawayView(self.cog, None)
        message = await interaction.channel.send(embed=embed, view=view)
        gid = message.id
        view.gid = gid

        self.cog.giveaways[gid] = {
            "prize": self.prize.value,
            "winners": win_count,
            "end_time": end_time,
            "host": host_id,
            "channel": interaction.channel.id,
            "message": message,
            "entries": set()
        }
        self.cog.save_giveaways(interaction.guild.id)
        self.cog.bot.loop.create_task(self.cog.update_giveaway_message(gid))

        await interaction.response.send_message(f"✅ Giveaway started in {interaction.channel.mention}!", ephemeral=True)

# ─── The Cog ───────────────────────────────────────────────────────────────────

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways = {}
        os.makedirs("giveaway", exist_ok=True)
        self.bot.loop.create_task(self.load_giveaways())

    async def load_giveaways(self):
        await self.bot.wait_until_ready()
        for fn in os.listdir("giveaway"):
            if not fn.endswith(".json"): continue
            guild_id = int(fn[:-5])
            path = os.path.join("giveaway", fn)
            with open(path) as f:
                data = json.load(f)
            guild = self.bot.get_guild(guild_id)
            if not guild: continue
            for gid_str, g in data.items():
                gid = int(gid_str)
                channel = guild.get_channel(g["channel"])
                if not channel: continue
                try:
                    message = await channel.fetch_message(g["message"])
                except discord.NotFound:
                    continue

                end_time = datetime.fromisoformat(g["end_time"])
                entries = set(g.get("entries", []))

                self.giveaways[gid] = {
                    "prize": g["prize"],
                    "winners": g["winners"],
                    "end_time": end_time,
                    "host": g["host"],
                    "channel": g["channel"],
                    "message": message,
                    "entries": entries
                }
                view = GiveawayView(self, gid)
                await message.edit(view=view)
                self.bot.loop.create_task(self.update_giveaway_message(gid))

    def save_giveaways(self, guild_id):
        path = os.path.join("giveaway", f"{guild_id}.json")
        to_save = {}
        for gid, g in self.giveaways.items():
            if self.bot.get_channel(g["channel"]):
                to_save[gid] = {
                    "prize": g["prize"],
                    "winners": g["winners"],
                    "end_time": g["end_time"].isoformat(),
                    "host": g["host"],
                    "channel": g["channel"],
                    "message": g["message"].id,
                    "entries": list(g["entries"])
                }
        with open(path, "w") as f:
            json.dump(to_save, f, indent=4)

    async def update_giveaway_message(self, gid: int):
        while gid in self.giveaways:
            g = self.giveaways[gid]
            now = datetime.now(timezone.utc)
            if now >= g["end_time"]:
                return await self.end_giveaway(gid)
            host_member = (
                g["message"].guild.get_member(g["host"]) or self.bot.get_user(g["host"])  
            )
            embed = create_giveaway_embed(
                g["prize"],
                g["end_time"],
                host_member,
                len(g["entries"]),
                g["winners"]
            )
            try:
                await g["message"].edit(embed=embed)
            except:
                pass
            await asyncio.sleep(10)

    async def end_giveaway(self, gid: int):
        g = self.giveaways.pop(gid, None)
        if not g:
            return

        channel = self.bot.get_channel(g["channel"])
        participants = list(g["entries"])
        host_user = channel.guild.get_member(g["host"]) or self.bot.get_user(g["host"]) 

        # Determine ticket channel from /logs settings
        settings_path = f"server_data/{channel.guild.id}_settings.json"
        ticket_channel = None
        if os.path.exists(settings_path):
            try:
                with open(settings_path) as sf:
                    settings_data = json.load(sf)
                ch_id = settings_data.get("giveaway_log")
                if ch_id:
                    ticket_channel = f"<#{ch_id}>"
            except Exception:
                pass
        ticket_channel = ticket_channel or "#open_ticket_channel"

        win_embed = discord.Embed(
            title=" 🎉 Congratulations!",
            color=discord.Color.pink()
        )

        desc_lines = [f"**Prize:** {g['prize']}"]
        winner_mentions = []

        if participants:
            winners = random.sample(participants, min(len(participants), g['winners']))
            for uid in winners:
                user = channel.guild.get_member(uid) or await self.bot.fetch_user(uid)
                if user:
                    winner_mentions.append(user.mention)
            desc_lines.append(f"**Winner(s):** {', '.join(winner_mentions)}")
        else:
            desc_lines.append("**Winner(s):** No valid entries.")

        desc_lines.append(f"**Hosted by:** {host_user.mention}")
        desc_lines.append("\n--------------------------")
        desc_lines.append(f"- Open a ticket in {ticket_channel}")
        desc_lines.append("- Please take a screenshot of this message and send it in your claim ticket!")

        win_embed.description = "\n".join(desc_lines)

        # Send the ping and embed together
        if winner_mentions:
            await channel.send(content= "🎉" + " ".join(winner_mentions), embed=win_embed)
        else:
            await channel.send(embed=win_embed)

        self.save_giveaways(channel.guild.id)

    # Helper method to check if user has Staff Team or higher role
    def has_staff_or_above(self, member: discord.Member):
        staff_role = discord.utils.get(member.guild.roles, name="Staff Team")
        if not staff_role:
            return False  # Staff Team role not found, deny access just in case
        member_highest = member.top_role
        return member_highest >= staff_role

    @app_commands.command(name="gcreate", description="Create a giveaway via form")
    async def gcreate(self, interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            return await interaction.response.send_message("❌ You must be in a server to use this command.", ephemeral=True)

        if not self.has_staff_or_above(member):
            return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

        await interaction.response.send_modal(GiveawayModal(self, interaction))

async def setup(bot):
    await bot.add_cog(Giveaway(bot))