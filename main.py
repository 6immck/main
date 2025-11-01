import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import random

# -------------------- flask keep-alive setup --------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# -------------------- discord intents and bot setup --------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------- GAMES DROPDOWN --------------------
class GamesDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="deadbydaylight"),
            discord.SelectOption(label="rust"),
            discord.SelectOption(label="overwatch"),
            discord.SelectOption(label="rivals"),
            discord.SelectOption(label="valorant"),
            discord.SelectOption(label="fortnite")
        ]
        super().__init__(placeholder="Choose your game role...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_role = self.values[0]
        role = discord.utils.get(interaction.guild.roles, name=selected_role)
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"Removed role: {role.name}", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Added role: {role.name}", ephemeral=True)
        else:
            await interaction.response.send_message("Role not found.", ephemeral=True)

class GamesView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(GamesDropdown())

def create_games_embed():
    embed = discord.Embed(
        title="__choose game roles ☆⋆__",
        color=discord.Color.from_rgb(4, 4, 4)
    )
    embed.add_field(
        name="\u200B↓\u200B",
        value="\n".join([
            "<:30379blackheart:1433934665919496202> ． deadbydaylight",
            "<:30379blackheart:1433934665919496202> ． rust",
            "<:30379blackheart:1433934665919496202> ． overwatch",
            "<:30379blackheart:1433934665919496202> ． minecraft",
            "<:30379blackheart:1433934665919496202> ． valorant",
            "<:30379blackheart:1433934665919496202> ． fortnite"
        ]),
        inline=False
    )
    # invisible top-right "spacer"
    embed.set_thumbnail(url="https://i.imgur.com/xkBPQe8.png")
    return embed

# -------------------- COLOURS DROPDOWN --------------------
class ColoursDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="★⋆˙ red"),
            discord.SelectOption(label="✮⋆˙ white"),
            discord.SelectOption(label="☆⋆˙ gray"),
            discord.SelectOption(label="✦⋆˙ black"),
            discord.SelectOption(label="✶⋆˙ purple"),
            discord.SelectOption(label="⋆𐙚̊. pink")
        ]
        super().__init__(placeholder="Choose your colour role...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        label_to_role = {
            "★⋆˙ red": "★⋆˙",
            "✮⋆˙ white": "✮⋆˙",
            "☆⋆˙ gray": "☆⋆˙",
            "✦⋆˙ black": "✦⋆˙",
            "✶⋆˙ purple": "✶⋆˙",
            "⋆𐙚̊. pink": "⋆𐙚̊."
        }

        selected_label = self.values[0]
        role_name = label_to_role.get(selected_label)

        if not role_name:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return

        # Get the new role object
        new_role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not new_role:
            await interaction.response.send_message("Role not found in the server.", ephemeral=True)
            return

        # Remove any other colour roles the user has
        colour_roles = [discord.utils.get(interaction.guild.roles, name=r) for r in label_to_role.values()]
        roles_to_remove = [r for r in colour_roles if r in interaction.user.roles and r != new_role]
        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        # Toggle the selected role
        if new_role in interaction.user.roles:
            await interaction.user.remove_roles(new_role)
            await interaction.response.send_message(f"Removed role: {new_role.name}", ephemeral=True)
        else:
            await interaction.user.add_roles(new_role)
            await interaction.response.send_message(f"Added role: {new_role.name}", ephemeral=True)

class ColoursView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ColoursDropdown())

def create_colours_embed():
    embed = discord.Embed(
        title="__choose colour roles‧₊˚__",
        color=discord.Color.from_rgb(4, 4, 4)
    )
    embed.add_field(
        name="\u200B↓\u200B",
        value="\n".join([
            "<a:71329butterfliesred:1433962590752604241> ． red ★",
            "<a:1butterflys:1433931924895830026> ． white ᯓ",
            "<a:92149uzigrey:1433975133684633650> ． gray ☆",
            "<a:51011uziblack:1433972913895374958> ． black 𓍼",
            "<a:66721butterflypurple:1433935080606273586> ． purple ★",
            "<a:8838butterflypink:1433935561638543562> ． pink 𐙚̊"
        ]),
        inline=False
    )
    embed.set_thumbnail(url="https://i.imgur.com/xkBPQe8.png")  # invisible image
    return embed

# -------------------- PERSISTENT MENU --------------------
class GamesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GamesDropdown())

class ColoursView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColoursDropdown())

# -------------------- ROLE MENU COMMAND --------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def roles(ctx):
    await ctx.send(embed=create_games_embed(), view=GamesView())
    await ctx.send(embed=create_colours_embed(), view=ColoursView())

@roles.error
async def roles_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{ctx.author.mention}, you do not have permission to run this command.")

# -------------------- PING COMMAND --------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"{ctx.author.mention} latency: {latency}ms")

# -------------------- NEW MEMBER GREETING --------------------
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='⋅˚₊‧-୨୧-‧₊˚-⋅')
    if channel:
        embed = discord.Embed(
            title=f"˖⁺‧₊˚ welcome to {member.guild.name} ˚₊‧⁺˖",
            description=(
                f"╭┈┈┈┈┈┈┈┈┈┈ ⋆｡°✩\n"
                f"┊ hey {member.mention} ♡\n"
                f"┊\n"
                f"┊˚₊‧    ☆    ‧₊˚\n"
                f"┊\n"
                f"┊ pick your roles in <#1423910903979442277>\n"
                f"╰┈┈┈┈┈┈┈┈┈┈ ⋆｡°✩"
            ),
            color=discord.Color.from_rgb(95, 48, 112)
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_image(url="https://i.imgur.com/vL3vMhC.jpeg")
        embed.set_footer(text="be normal ;3 | welcome ♱", icon_url=member.avatar.url)
        await channel.send(embed=embed)

    new_member_role = discord.utils.get(member.guild.roles, name="member ♱")
    if new_member_role:
        await member.add_roles(new_member_role)

# -------------------- TEST CMD --------------------
@bot.command()
async def test(ctx):
    await ctx.send(f"{ctx.author.mention} kys lol")

# -------------------- COIN FLIP EMBED COMMAND --------------------
@bot.command()
async def coinflip(ctx, guess: str = None):
    """
    flip a virtual coin
    optional: user can guess 'heads' or 'tails'.
    """
    result = random.choice(["heads", "tails"])

    # Create the embed
    embed = discord.Embed(
        title="🪙 coin flip!",
        description=f"{ctx.author.mention} flipped a coin...",
        color=discord.Color.from_rgb(255, 105, 180)  # pink sparkle tone
    )

    # Add result
    if guess:
        guess = guess.lower()
        if guess not in ["heads", "tails"]:
            embed.description += "\n❌ please guess either 'heads' or 'tails'!"
            await ctx.send(embed=embed)
            return
        if guess == result:
            embed.add_field(name="result", value=f" the coin landed on **{result}** you guessed correctly!", inline=False)
        else:
            embed.add_field(name="result", value=f" the coin landed on **{result}** lol kys", inline=False)
    else:
        embed.add_field(name="result", value=f"the coin landed on **{result}**!", inline=False)

    await ctx.send(embed=embed)

# -------------------- CLEAR COMMAND --------------------
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 2):
        """
        clear messages in a channel
        default: 2 messages
        """
        deleted = await ctx.channel.purge(limit=amount)
        confirmation = await ctx.send(f"deleted {len(deleted)} messages.")
        await ctx.send(f"deleted {len(deleted)} messages.", delete_after=5)

# -------------------- keep bot alive --------------------
keep_alive()  # start Flask server if you’re using Replit or similar
bot.run(os.getenv("TOKEN"))  # actually connect your bot to Discord
