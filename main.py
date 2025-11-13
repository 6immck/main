import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import os
import random

# -------------------- discord intents and bot setup --------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!6", intents=intents)

# create /6 command group
class SixGroup(app_commands.Group):
    @app_commands.command(name="count", description="show the current count in this channel")
    async def count_cmd(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("CountingGame")
        if not cog:
            await interaction.response.send_message("counting game not loaded.")
            return
        d = cog.get_data(interaction.channel.id)
        await interaction.response.send_message(f"current count: {d['next'] - 1}")
    def __init__(self):
        super().__init__(name="6", description="6immck bot commands")

    # -------------------- economy: beg --------------------
    @app_commands.command(name="beg", description="try your luck to earn coins")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def beg(self, interaction: discord.Interaction):
        events = [
            {"text": "joey's saudi arabian muslim family gave you {amount} coins.", "min": 50, "max": 500},
            {"text": "you found a wallet on the ground with {amount} coins.", "min": 20, "max": 150},
            {"text": "you found hayden playing clash royale at the function, robbed him and made {amount} coins.", "min": 10, "max": 100},
            {"text": "lord gimmick felt generous and gave you {amount} coins", "min": 200, "max": 500},
            {"text": "hayden beat the shit out of you and you lost {amount} coins", "min": -60, "max": -10},
        ]
        event = random.choice(events)
        amount = random.randint(event["min"], event["max"])
        update_balance(interaction.user.id, amount)

        if amount > 0:
            color = discord.Color.from_rgb(0, 255, 0)
            result = f"🪙 you gained **{amount}** coins!"
        else:
            color = discord.Color.from_rgb(252, 63, 63)
            result = f"💸 you lost **{abs(amount)}** coins!"

        embed = discord.Embed(
            title="💰",
            description=f"{interaction.user.mention}, {event['text'].format(amount=abs(amount))}\n\n{result}",
            color=color
        )
        embed.set_footer(text="use /6 bal to check your balance")
        await interaction.response.send_message(embed=embed)

    # -------------------- balance --------------------
    @app_commands.command(name="bal", description="check your or another user's balance")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None):
        user = member or interaction.user
        balance = get_balance(user.id)
        await interaction.response.send_message(f"{user.mention} has 💰 {balance} coins.")

    # -------------------- coinflip --------------------
    @app_commands.command(name="coinflip", description="bet coins on a coin toss")
    @app_commands.describe(amount="amount to bet", guess="your guess: heads or tails")
    async def coinflip(self, interaction: discord.Interaction, amount: int, guess: str):
        guess = guess.lower()
        if guess in ["heads", "h", "head"]:
            guess = "heads"
        elif guess in ["t", "tail", "tails"]:
            guess = "tails"
        else:
            await interaction.response.send_message("choose heads or tails. (/6 coinflip [amount] [heads/tails])")
            return

        balance = get_balance(interaction.user.id)
        if amount <= 0:
            await interaction.response.send_message("bet amount must be greater than 0.")
            return
        if amount > balance:
            await interaction.response.send_message("you don’t have enough coins to bet that much.")
            return

        result = random.choice(["heads", "tails"])
        if result == guess:
            update_balance(interaction.user.id, amount)
            title = "🎉 you won!"
            result_text = f"the coin landed on **{result}** — you won 💸 **{amount}** coins!"
            color = discord.Color.green()
        else:
            update_balance(interaction.user.id, -amount)
            title = "<:emoji_45:1433976464063332503> you lost!"
            result_text = f"the coin landed on **{result}** — you lost 💸 **{amount}** coins."
            color = discord.Color.red()

        new_balance = get_balance(interaction.user.id)
        embed = discord.Embed(
            title=title,
            description=f"{interaction.user.mention}, {result_text}\n\n💰 **your new balance:** {new_balance} coins.",
            color=color
        )
        embed.set_footer(text="use /6 bal to check your balance")
        await interaction.response.send_message(embed=embed)

    # -------------------- blackjack --------------------
    @app_commands.command(name="blackjack", description="play blackjack with coins")
    @app_commands.describe(bet="amount to bet")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        if interaction.user.id in active_blackjack_games:
            await interaction.response.send_message("you're already in a blackjack game.", ephemeral=True)
            return
        if bet <= 0:
            await interaction.response.send_message("bet must be greater than 0.")
            return
        balance = get_balance(interaction.user.id)
        if bet > balance:
            await interaction.response.send_message("you don’t have enough coins to bet that much.")
            return
        active_blackjack_games.add(interaction.user.id)
        view = BlackjackView(interaction, bet)
        await view.update_embed()

    # -------------------- donate --------------------
    @app_commands.command(name="donate", description="send coins to another user")
    @app_commands.describe(member="person to donate to", amount="amount to send")
    async def donate(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("donate amount must be greater than 0.")
            return
        sender_balance = get_balance(interaction.user.id)
        if amount > sender_balance:
            await interaction.response.send_message("you don’t have enough coins to donate.")
            return

        update_balance(interaction.user.id, -amount)
        update_balance(member.id, amount)
        embed = discord.Embed(
            title="donation successful",
            description=(
                f"{interaction.user.mention} gave **{amount}** coins to {member.mention} <3\n\n"
                f"💰 **{interaction.user.display_name}'s new balance:** {get_balance(interaction.user.id)} coins\n"
                f"💰 **{member.display_name}'s new balance:** {get_balance(member.id)} coins"
            ),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text="⋆𐙚 ̊.")
        await interaction.response.send_message(embed=embed)

    # -------------------- help --------------------
    @app_commands.command(name="help", description="show help menu")
    async def sixhelp(self, interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator
        embed = discord.Embed(
            title="main commands",
            description="\n".join([
                "/6 ping - show latency",
                "/6 hayden - shows a hideous idiot",
                "/6 test - test if bot is up",
                "/6 help - show this menu"
            ]),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        view = HelpView(is_admin)
        await interaction.response.send_message(embed=embed, view=view)

    # -------------------- ping --------------------
    @app_commands.command(name="ping", description="show latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f"{interaction.user.mention} latency: {latency}ms")

    # -------------------- test --------------------
    @app_commands.command(name="test", description="check if bot is up")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{interaction.user.mention} up")

    # -------------------- hayden --------------------
    @app_commands.command(name="hayden", description="shows a hideous idiot")
    async def hayden(self, interaction: discord.Interaction):
        image_url = "https://i.imgur.com/ZFW9ZsW.jpeg"
        await interaction.response.send_message(image_url)

    # -------------------- clear --------------------
    @app_commands.command(name="clear", description="clear messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 2):
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"deleted {len(deleted)} messages.", ephemeral=True)

    # -------------------- roles --------------------
    @app_commands.command(name="roles", description="post role menus")
    @app_commands.checks.has_permissions(administrator=True)
    async def roles(self, interaction: discord.Interaction):
        await interaction.response.send_message("posting role menus...", ephemeral=True)
        await interaction.channel.send(embed=create_games_embed(), view=GamesView())
        await interaction.channel.send(embed=create_colours_embed(), view=ColoursView())

# register group
bot.tree.add_command(SixGroup())

# ------------- continue BlackjackView (same logic as your original) -------------
class BlackjackView(discord.ui.View):
    def __init__(self, interaction, bet):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.ctx = interaction  # to reuse your old naming
        self.bet = bet
        self.player_total = random.randint(2, 11) + random.randint(2, 11)
        self.dealer_total = random.randint(2, 11)
        self.standing = False

    async def update_embed(self, interaction: discord.Interaction = None, end=False):
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

            update_balance(self.ctx.user.id, change)
            new_balance = get_balance(self.ctx.user.id)

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
            embed.set_footer(text="use /6 bal to check your balance")

            for child in self.children:
                child.disabled = True

            if self.ctx.user.id in active_blackjack_games:
                active_blackjack_games.remove(self.ctx.user.id)

            if interaction:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await self.ctx.followup.send(embed=embed)
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
            # first message
            await self.ctx.followup.send(embed=embed, view=self)

    async def on_timeout(self):
        if self.ctx.user.id not in active_blackjack_games:
            return
        for child in self.children:
            child.disabled = True

        if self.ctx.user.id in active_blackjack_games:
            active_blackjack_games.remove(self.ctx.user.id)

        penalty = self.bet // 2
        update_balance(self.ctx.user.id, -penalty)

        embed = discord.Embed(
            title="♠ blackjack ♠",
            description=f"⏰ time's up! you lost **{penalty}** coins for inactivity.",
            color=discord.Color.red()
        )
        # send to the same channel user used the command in
        await self.ctx.followup.send(embed=embed, delete_after=60)

    @discord.ui.button(label="HIT", style=discord.ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message("this isn’t your game.", ephemeral=True)
        self.player_total += random.randint(2, 11)
        if self.player_total > 21:
            await self.update_embed(interaction, end=True)
        else:
            await self.update_embed(interaction)

    @discord.ui.button(label="STAND", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.user.id:
            return await interaction.response.send_message("this isn’t your game.", ephemeral=True)
        self.standing = True
        await self.update_embed(interaction, end=True)


# ------------- HelpView (kept same style, just updated to /6 text) -------------
class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool):
        super().__init__(timeout=60)
        self.is_admin = is_admin

    @discord.ui.button(label="all cmnds", style=discord.ButtonStyle.primary)
    async def main_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="all commands",
            description="\n\n".join([
                "/6 ping - show latency",
                "/6 hayden - shows a hideous idiot",
                "/6 test - test if bot is up",
                "/6 help - show this menu"
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
                "/6 clear - clear messages",
                "/6 roles - post role menus"
            ]),
            color=discord.Color.from_rgb(255, 225, 255)
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="currency", style=discord.ButtonStyle.success)
    async def currency_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="currency commands",
            description="\n\n".join([
                "/6 bal [@user] - check your or another user’s balance",
                "/6 beg - try your luck to earn coins",
                "/6 coinflip [amount] [heads/tails] - bet coins on a coin toss",
                "/6 donate [@user] [amount] - send coins to someone else",
            ]),
            color=discord.Color.from_rgb(255, 255, 255)
        )
        await interaction.response.edit_message(embed=embed, view=self)


# ---- games dropdown menu (unchanged) --------------------
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
            await interaction.response.send_message("role not found.", ephemeral=True)
            return

        colour_roles = [discord.utils.get(interaction.guild.roles, name=r) for r in label_to_role.values()]
        roles_to_remove = [r for r in colour_roles if r in interaction.user.roles and r != new_role]
        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        if new_role in interaction.user.roles:
            await interaction.user.remove_roles(new_role)
            await interaction.response.send_message(f"removed colour: {new_role.name}", ephemeral=True)
        else:
            await interaction.user.add_roles(new_role)
            await interaction.response.send_message(f"added colour: {new_role.name}", ephemeral=True)


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
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text="be normal ;3 | welcome ♱", icon_url=member.avatar.url)
        embed.set_image(url="https://i.imgur.com/vL3vMhC.jpeg")
        await channel.send(embed=embed)

    role = discord.utils.get(member.guild.roles, name="ִ ࣪✮ 🕷 ✮⋆˙")
    if role:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            print("⚠️ Missing permission to assign join role.")


# -------------------- counting minigame (kept as-is) --------------------

class CountingGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_data = {}

    def get_data(self, channel_id: int):
        if channel_id not in self.channel_data:
            self.channel_data[channel_id] = {"next": 1, "last_user": None, "participants": set()}
        return self.channel_data[channel_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if isinstance(self.bot.command_prefix, str) and message.content.startswith(self.bot.command_prefix):
            return

        data = self.get_data(message.channel.id)

        try:
            num = int(message.content.strip())
        except:
            return

        expected = data["next"]

        if data["last_user"] == message.author.id:
            await message.channel.send(f"{message.author.mention} you can’t count twice in a row! restarting at 1.")
            data.update({"next": 1, "last_user": None, "participants": set()})
            return

        if num == expected:
            data["next"] += 1
            data["last_user"] = message.author.id
            data["participants"].add(message.author.id)

            await message.add_reaction("✅")

            milestone = None
            if expected in [10, 20, 50, 75]:
                milestone = expected
            elif expected < 1000 and expected % 25 == 0:
                milestone = expected
            elif expected >= 1000 and expected % 50 == 0:
                milestone = expected

            if milestone:
                reward = milestone if milestone <= 1000 else 1000
                for uid in data["participants"]:
                    update_balance(uid, reward)
                await message.channel.send(
                    f"🎉 milestone reached! count hit {milestone} — everyone who participated earned {reward} coins!"
                )
        else:
            await message.channel.send(f"{message.author.mention} messed up! expected `{expected}`, restarting at 1.")
            data.update({"next": 1, "last_user": None, "participants": set()})

async def setup_cogs():
    await bot.add_cog(CountingGame(bot))

# Run it right after bot is ready
@bot.event
async def on_ready():
    print(f"✅ logged in as {bot.user}")

    await setup_cogs()  # <-- add this line

    bot.add_view(GamesView())
    bot.add_view(ColoursView())

    try:
        await bot.tree.sync()
        print("✅ slash commands synced.")
    except Exception as e:
        print("❌ slash sync failed:", e)

# -------------------- flask keep-alive setup --------------------
from flask import request
from datetime import datetime
import requests, time, threading

app = Flask(__name__)

@app.route('/')
def home():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_agent = request.headers.get('User-Agent', 'Unknown')

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

def self_ping():
    while True:
        try:
            # change to your real render url or env
            requests.get(os.getenv("RENDER_URL", "https://main-bfc1.onrender.com/"))
            print("🔁 self-ping sent to Render")
        except Exception as e:
            print("⚠️ self-ping failed:", e)
        time.sleep(300)

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

# set prefix so counting game can ignore "!6" like before


# global handler for slash cooldowns (replacement for your old beg_error)
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏳ you’re on cooldown! try again in {error.retry_after:.1f} seconds.",
            ephemeral=True
        )
    else:
        # optional: print for debug
        print("slash error:", error)

# -------------------- Keep bot alive --------------------
keep_alive()
bot.run(os.getenv("TOKEN"))
