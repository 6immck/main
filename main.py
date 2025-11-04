import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import os
import random

# -------------------- discord intents and bot setup, !command --------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!6", intents=intents)
bot.remove_command("help")

#MONGO-6IMMCKECONOMY - PERSISTENT -------------------------------

#beg
@bot.command(name="beg")
@commands.cooldown(1, 10, commands.BucketType.user)
async def beg(ctx):
    events = [
        {"text": "joey's saudi arabian muslim family gave you {amount} coins.", "min": 50, "max": 500},
        {"text": "you found a wallet on the ground with {amount} coins.", "min": 20, "max": 150},
        {"text": "you found hayden playing clash royale at the function, robbed him and made {amount} coins.", "min": 10, "max": 100},
        {"text": "lord gimmick felt generous and gave you {amount} coins", "min": 200, "max": 500},
        {"text": "hayden beat the shit out of you and you lost {amount} coins", "min": -60, "max": -10},
    ]

    event = random.choice(events)
    amount = random.randint(event["min"], event["max"])
    update_balance(ctx.author.id, amount)

    # color + message formatting
    if amount > 0:
        color = discord.Color.from_rgb(0, 255, 0)
        result = f"🪙 you gained **{amount}** coins!"
    else:
        color = discord.Color.from_rgb(252, 63, 63)
        result = f"💸 you lost **{abs(amount)}** coins!"

    # create embed
    embed = discord.Embed(
        title="💰",
        description=f"{ctx.author.mention}, {event['text'].format(amount=abs(amount))}\n\n{result}",
        color=color
    )
    embed.set_footer(text="use !6bal to check your balance")

    await ctx.send(embed=embed)

#balance
@bot.command(name="bal")
async def balance(ctx, member: discord.Member = None):
    user = member or ctx.author
    balance = get_balance(user.id)
    await ctx.send(f"{user.mention} has 💰 {balance} coins.")

#begcooldown
async def beg_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ you’re on cooldown! try again in {error.retry_after:.1f} seconds.", delete_after=5)

#coinflip
@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx, amount: int, guess: str):
    guess = guess.lower()
    if guess in ["heads", "h", "head"]:
        guess = "heads"
    elif guess in ["t", "tail", "tails"]:
        guess = "tails"
    else:
       await ctx.send("choose heads or tails. (!6coinflip/cf [amount] [heads/tails])")
       return

    balance = get_balance(ctx.author.id)
    if amount <= 0:
        await ctx.send("bet amount must be greater than 0.")
        return
    if amount > balance:
        await ctx.send("you don’t have enough coins to bet that much.")
        return

    result = random.choice(["heads", "tails"])
    if result == guess:
        update_balance(ctx.author.id, amount)
        title = "🎉 you won!"
        result_text = f"the coin landed on **{result}** — you won 💸 **{amount}** coins!"
        color = discord.Color.green()
    else:
        update_balance(ctx.author.id, -amount)
        title = "<:emoji_45:1433976464063332503> you lost!"
        result_text = f"the coin landed on **{result}** — you lost 💸 **{amount}** coins."
        color = discord.Color.red

    new_balance = get_balance(ctx.author.id)

    embed = discord.Embed(
        title=title,
        description=f"{ctx.author.mention}, {result_text}\n\n💰 **your new balance:** {new_balance} coins.",
        color=color
    )
    embed.set_footer(text="use !6bal to check your balance")
    await ctx.send(embed=embed)


#blackjack ----------------------------------------------------------------
active_blackjack_games = set()

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.player_total = random.randint(2, 11) + random.randint(2, 11)
        self.dealer_total = random.randint(2, 11)
        self.standing = False

    async def update_embed(self, interaction=None, end=False):
        if end:
            while self.dealer_total < 17:
                self.dealer_total += random.randint(2, 11)

            if self.player_total > 21:
                result = "✕ you busted!"
                color = discord.Color.red()
                change = -self.bet
            elif self.dealer_total > 21 or self.player_total > self.dealer_total:
                result = "✓ you win!"
                color = discord.Color.green()
                change = self.bet
            elif self.player_total < self.dealer_total:
                result = "✕ dealer wins!"
                color = discord.Color.red()
                change = -self.bet
            else:
                result = "𖧋 it's a tie!"
                color = discord.Color.from_rgb(255, 255, 255)
                change = 0

            update_balance(self.ctx.author.id, change)
            new_balance = get_balance(self.ctx.author.id)

            embed = discord.Embed(
                title="♠ blackjack results",
                description=(
                    "╭──────────────────────────────╮\n"
                    f"‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎**your total:** {self.player_total}\n"
                    f"‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎**dealer's total:** {self.dealer_total}\n"
                    "╰──────────────────────────────╯\n\n"
                    f"{result}\n\n"
                    f"💰 **your new balance:** {new_balance} coins"
                ),
                color=color
            )
            embed.set_footer(text="use !6bal to check your balance")

            for child in self.children:
                child.disabled = True

            if self.ctx.author.id in active_blackjack_games:
                active_blackjack_games.remove(self.ctx.author.id)

            if interaction:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await self.ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="♠️ blackjack ♠",
            description=(
                "╭──────────────────────────────╮\n"
                f" ‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎**your total:** {self.player_total}\n"
                f"‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎‎ **dealer shows:** {self.dealer_total}\n"
                "╰──────────────────────────────╯\n\n"
                f"🃏 hit to draw, or stand to end your turn."
            ),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        embed.set_footer(text="blackjack ♠ | 6immck")

        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await self.ctx.send(embed=embed, view=self)

    async def on_timeout(self):
        if self.ctx.author.id not in active_blackjack_games:
            return
        for child in self.children:
            child.disabled = True

        if self.ctx.author.id in active_blackjack_games:
            active_blackjack_games.remove(self.ctx.author.id)

        penalty = self.bet // 2
        update_balance(self.ctx.author.id, -penalty)

        embed = discord.Embed(
            title="♠ blackjack ♠",
            description=f"⏰ time's up! you lost **{penalty}** coins for inactivity.",
            color=discord.Color.red()
        )
        await self.ctx.send(embed=embed, delete_after=60)

    @discord.ui.button(label="HIT", style=discord.ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("this isn’t your game.", ephemeral=True)
        self.player_total += random.randint(2, 11)
        if self.player_total > 21:
            await self.update_embed(interaction, end=True)
        else:
            await self.update_embed(interaction)

    @discord.ui.button(label="STAND", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("this isn’t your game.", ephemeral=True)
        self.standing = True
        await self.update_embed(interaction, end=True)

# keep this at the end — your command handler
@bot.command(name="blackjack", aliases=["bj"])
async def blackjack(ctx, bet: int):
    if ctx.author.id in active_blackjack_games:
        await ctx.send("you're already in a blackjack game. finish it before starting a new one.", delete_after=5)
        return

    if bet <= 0:
        await ctx.send("bet must be greater than 0.")
        return

    balance = get_balance(ctx.author.id)
    if bet > balance:
        await ctx.send("you don’t have enough coins to bet that much.")
        return

    active_blackjack_games.add(ctx.author.id)

    view = BlackjackView(ctx, bet)
    await view.update_embed()

#donate -----------------------CMD------------------------------------


@bot.command(name="donate")
async def donate(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("donate amount must be greater than 0.")
        return

    sender_balance = get_balance(ctx.author.id)
    if amount > sender_balance:
        await ctx.send("you don’t have enough coins to donate.")
        return

    # Update both balances
    update_balance(ctx.author.id, -amount)
    update_balance(member.id, amount)

    # Create a nice embed
    embed = discord.Embed(
        title="donation successful",
        description=(
            f"{ctx.author.mention} gave **{amount}** coins to {member.mention} <3\n\n"
            f"💰 **{ctx.author.display_name}'s new balance:** {get_balance(ctx.author.id)} coins\n"
            f"💰 **{member.display_name}'s new balance:** {get_balance(member.id)} coins"
        ),
        color=discord.Color.from_rgb(255, 255, 255)
    )

    # Show both avatars in the embed
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)

    embed.set_footer(text="⋆𐙚 ̊.")

    await ctx.send(embed=embed)

# -------------------- flask keep-alive setup --------------------
# -------------------- flask keep-alive setup --------------------
from flask import Flask, request
from datetime import datetime
import requests, time, threading, os
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_agent = request.headers.get('User-Agent', 'Unknown')

    # identify which service is pinging
    if "UptimeRobot" in user_agent:
        source = "🌐 UptimeRobot"
    elif "BetterStack" in user_agent or "Better Uptime" in user_agent:
        source = "🧭 BetterStack"
    elif "python-requests" in user_agent:
        source = "🤖 Self-Pinger"
    else:
        source = "🕵️ Other"

    print(f"{source} → Ping received at {now}")
    return "Bot is alive and running on Render!"

# optional: self-pinger to keep Render awake
def self_ping():
    while True:
        try:
            requests.get("https://main-bfc1.onrender.com/")  # or /health if you add one later
            print("🔁 self-ping sent to Render")
        except Exception as e:
            print("⚠️ self-ping failed:", e)
        time.sleep(300)  # every 5 minutes

# start the background self-ping thread
threading.Thread(target=self_ping, daemon=True).start()

def run():
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Flask server running on port {port}")
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    thread = Thread(target=run)
    thread.start()

# -------------------- MongoDB Setup --------------------
print("Connecting to MongoDB...")
import certifi

uri = os.getenv("MONGO_URI")
if not uri:
    raise ValueError("❌ MONGO_URI not set in environment variables")

client = MongoClient(uri, tls=True, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)

try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully.")
except Exception as e:
    print("❌ MongoDB connection failed:", e)

db = client["economy"]
users = db["balances"]

def get_balance(user_id):
    user = users.find_one({"_id": user_id})
    return user["balance"] if user else 0

def update_balance(user_id, amount):
    users.update_one({"_id": user_id}, {"$inc": {"balance": amount}}, upsert=True)


#!6help displays all commands for my bot -------------------------------------------------!!!!!!!!!!!
class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool):
        super().__init__(timeout=60)
        self.is_admin = is_admin

    @discord.ui.button(label="all cmnds", style=discord.ButtonStyle.primary)
    async def main_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="all commands",
            description="\n\n".join([
                "!6ping - show latency",
                "!6hayden - shows a hideous idiot",
                "!6test - test if bot is up",
                "!6help - show this menu"
            ]),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="admin cmnds", style=discord.ButtonStyle.danger)
    async def admin_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_admin:
            await interaction.response.send_message("you don't have permission to view admin commands.", ephemeral=True)
            return

        embed = discord.Embed(
            title="admin commands",
            description="\n".join([
                "!6clear - clear messages",
                "!6roles - post role menus"
            ]),
            color=discord.Color.from_rgb(255, 225, 255)
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="currency", style=discord.ButtonStyle.success)
    async def currency_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="currency commands",
            description="\n\n".join([
                "!6bal [@user] - check your or another user’s balance",
                "!6beg - try your luck to earn coins",
                "!6coinflip [amount] [heads/tails] - bet coins on a coin toss",
                "!6donate [@user] [amount] - send coins to someone else",
            ]),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(name="help")
async def sixhelp(ctx):
    is_admin = ctx.author.guild_permissions.administrator
    embed = discord.Embed(
        title="main commands",
        description="\n".join([
            "!6ping - show latency",
            "!6hayden - shows a hideous idiot",
            "!6test - test if bot is up",
            "!6help - show this menu"
        ]),
        color=discord.Color.from_rgb(255, 255, 255)
    )

    view = HelpView(is_admin)
    await ctx.send(embed=embed, view=view)

#!6ping to display latency -------------------------------------------------------
@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"{ctx.author.mention} latency: {latency}ms")

#!6test command to show bot's online status --------------------------------------
@bot.command()
async def test(ctx):
    await ctx.send(f"{ctx.author.mention} up")

#haydencommand !hayden------------------------------------------
@bot.command()
async def hayden(ctx):
    image_url = "https://i.imgur.com/ZFW9ZsW.jpeg"
    await ctx.send(image_url)

#clearcommand !clear----------------------------------------------
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 2):
    deleted = await ctx.channel.purge(limit=amount)
    confirmation = await ctx.send(f"deleted {len(deleted)} messages.", delete_after=5)

# ---- games dropdown menu --------------------
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
        super().__init__(placeholder="choose your game role...", min_values=1, max_values=1, options=options, custom_id="games_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected_role = self.values[0]
        role = discord.utils.get(interaction.guild.roles, name=selected_role)
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"removed role: {role.name}", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"added role: {role.name}", ephemeral=True)
        else:
            await interaction.response.send_message("role not found.", ephemeral=True)

class GamesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GamesDropdown())

def create_games_embed():
    embed = discord.Embed(
        title="__choose game roles ☆⋆__",
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.add_field(
        name="\u200B↓\u200B",
        value="\n".join([
            "<:52004black:1433934195222118593> ． deadbydaylight",
            "<:1023gun:1433947005381771305> ． rust",
            "<:1420coquetteknife:1433970746140393523> ． overwatch",
            "<:1962gothknife:1433938130896949280> ． rivals",
            "<:12673aaawings:1433931903387566261> ． valorant",
            "<:1paw:1433934253028020269> ． fortnite"
        ]),
        inline=False
    )
    embed.set_thumbnail(url="https://i.imgur.com/xkBPQe8.png")
    return embed

# -------------------- colours dropdown menu --------------------
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
        super().__init__(placeholder="choose your colour role...", min_values=1, max_values=1, options=options, custom_id="colours_dropdown")

    async def callback(self, interaction: discord.Interaction):
        label_to_role = {
            "★⋆˙ red": "★⋆˙",
            "✮⋆˙ white": "✮⋆˙",
            "☆⋆˙ gray": "☆⋆˙",
            "✦⋆˙ black": "✦⋆˙",
            "✶⋆˙ purple": "✶⋆˙",
            "⋆𐙚̊. pink": "⋆𐙚 ̊."
        }

        selected_label = self.values[0]
        role_name = label_to_role.get(selected_label)
        if not role_name:
            await interaction.response.send_message("role not found.", ephemeral=True)
            return

        new_role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not new_role:
            await interaction.response.send_message("role not found in the server.", ephemeral=True)
            return

        colour_roles = [discord.utils.get(interaction.guild.roles, name=r) for r in label_to_role.values()]
        roles_to_remove = [r for r in colour_roles if r in interaction.user.roles and r != new_role]
        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        if new_role in interaction.user.roles:
            await interaction.user.remove_roles(new_role)
            await interaction.response.send_message(f"removed : {new_role.name}", ephemeral=True)
        else:
            await interaction.user.add_roles(new_role)
            await interaction.response.send_message(f"u are now : {new_role.name}", ephemeral=True)

class ColoursView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColoursDropdown())

def create_colours_embed():
    embed = discord.Embed(
        title="__choose colour roles‧₊˚__",
        color=discord.Color.from_rgb(255, 255, 255)
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
    embed.set_thumbnail(url="https://i.imgur.com/xkBPQe8.png")
    return embed

# -------------------- role menu command --------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def roles(ctx):
    await ctx.send(embed=create_games_embed(), view=GamesView())
    await ctx.send(embed=create_colours_embed(), view=ColoursView())

@roles.error
async def roles_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{ctx.author.mention}, you do not have perms to use this command u peasant.")

# -------------------- Events and Commands --------------------
@bot.event
async def on_ready():
    print(f"✅ logged in as {bot.user}")

    bot.add_view(GamesView())
    bot.add_view(ColoursView())

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='⋅˚₊‧-୨୧-‧₊˚-⋅')
    if channel:
        embed = discord.Embed(
            title=f"˖⁺‧₊˚ welcome to {member.guild.name} ˚₊‧⁺˖",
            description=(
                f"╭┈┈┈┈┈┈┈┈┈┈ ⋆｡°✩\n"
                f"┊ hey {member.mention} ♡\n"
                f"┊ pick your roles in <#1423910903979442277>\n"
                f"╰┈┈┈┈┈┈┈┈┈┈ ⋆｡°✩"
            ),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_image(url="https://i.imgur.com/vL3vMhC.jpeg")
        embed.set_footer(text="be normal ;3 | welcome ♱", icon_url=member.avatar.url)
        await channel.send(embed=embed)

    role = discord.utils.get(member.guild.roles, name="ִ ࣪✮ 🕷 ✮⋆˙")
    if role:
        await member.add_roles(role)

# -------------------- Keep bot alive --------------------
keep_alive()
bot.run(os.getenv("TOKEN"))
