import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

DATA_DIR = "splitsteal_data"
os.makedirs(DATA_DIR, exist_ok=True)

class SplitStealView(discord.ui.View):
    def __init__(self, user1: discord.User, user2: discord.User, prize: str, host: discord.User, guild_id: int):
        super().__init__(timeout=None)
        self.user1 = user1
        self.user2 = user2
        self.host = host
        self.choices = {user1.id: None, user2.id: None}
        self.prize = prize
        self.message = None
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [self.user1.id, self.user2.id]:
            await interaction.response.send_message("You aren't part of this game.", ephemeral=True)
            return False
        return True

    async def make_choice(self, interaction: discord.Interaction, choice: str):
        if self.choices[interaction.user.id] is not None:
            await interaction.response.send_message("You already decided!", ephemeral=True)
            return

        self.choices[interaction.user.id] = choice
        await interaction.response.send_message(f"You chose **{choice}**.", ephemeral=True)

        if all(self.choices.values()):
            await self.reveal_results()
        else:
            embed = self.create_waiting_embed()
            await self.message.edit(embed=embed, view=self)

    def create_waiting_embed(self):
        if self.choices[self.user1.id] is None and self.choices[self.user2.id] is None:
            waiting_text = "Waiting for both players to choose!"
        elif self.choices[self.user1.id] is None:
            waiting_text = f"Waiting for {self.user1.mention} to choose!"
        elif self.choices[self.user2.id] is None:
            waiting_text = f"Waiting for {self.user2.mention} to choose!"
        else:
            waiting_text = "Processing..."

        embed = discord.Embed(title="⚠️ Split or Steal ⚠️", color=discord.Color.orange())
        embed.description = f"{waiting_text}\n" \
                            f"--------------------------\n" \
                            f"💰 **Prize:** {self.prize}"
        return embed

    async def reveal_results(self):
        user1_choice = self.choices[self.user1.id]
        user2_choice = self.choices[self.user2.id]

        embed = discord.Embed(title="⚠️ Results ⚠️", color=discord.Color.yellow())
        embed.add_field(name="", value=f"{self.user1.mention} chose **{user1_choice}**\n"
                                       f"{self.user2.mention} chose **{user2_choice}**", inline=False)
        embed.add_field(name="", value="--------------------------", inline=False)

        if user1_choice == "Split" and user2_choice == "Split":
            result = f"Both split {self.prize}"
            embed.add_field(name="", value=f"Both split **{self.prize}**!", inline=False)
        elif user1_choice == "Steal" and user2_choice == "Split":
            result = f"{self.user1.name} stole {self.prize}"
            embed.add_field(name="", value=f"{self.user1.mention} wins **{self.prize}**!", inline=False)
        elif user1_choice == "Split" and user2_choice == "Steal":
            result = f"{self.user2.name} stole {self.prize}"
            embed.add_field(name="", value=f"{self.user2.mention} wins **{self.prize}**!", inline=False)
        else:
            result = "Nobody won"
            embed.add_field(name="", value=f"No one wins **{self.prize}**!", inline=False)

        embed.set_footer(text=f"Giveaway hosted by @{self.host.name}")
        await self.message.channel.send(f"{self.user1.mention} and {self.user2.mention}, the game results are in!")
        await self.message.edit(embed=embed, view=self)

        await self.save_game(user1_choice, user2_choice, result)

    async def save_game(self, user1_choice, user2_choice, result):
        filepath = os.path.join(DATA_DIR, f"splitsteal_{self.guild_id}.json")
        game_data = {
            "user1_id": self.user1.id,
            "user2_id": self.user2.id,
            "host_id": self.host.id,
            "prize": self.prize,
            "user1_choice": user1_choice,
            "user2_choice": user2_choice,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
            else:
                data = []
            data.append(game_data)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Failed to save splitsteal game: {e}")

    @discord.ui.button(label="Split", style=discord.ButtonStyle.success)
    async def split_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.make_choice(interaction, "Split")

    @discord.ui.button(label="Steal", style=discord.ButtonStyle.danger)
    async def steal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.make_choice(interaction, "Steal")


class SplitStealCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="split_steal", description="Start a Split or Steal game")
    @app_commands.describe(user1="First player", user2="Second player", prize="Prize")
    async def split_steal(
        self, interaction: discord.Interaction, user1: discord.User, user2: discord.User, prize: str
    ):
        view = SplitStealView(user1, user2, prize, host=interaction.user, guild_id=interaction.guild.id)
        embed = view.create_waiting_embed()
        await interaction.response.send_message(
            f"{user1.mention} and {user2.mention}, the game is starting!",
            embed=embed,
            view=view
        )
        view.message = await interaction.original_response()

    async def cog_load(self):
        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(SplitStealCog(bot))
