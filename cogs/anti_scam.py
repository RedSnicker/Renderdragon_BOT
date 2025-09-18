<<<<<<< HEAD
import discord
from discord.ext import commands
import re
import os
import math
import random
import string
import time
from collections import defaultdict

# === CONFIGURABLE VALUES ===
SCAM_LINKS_FILE = "scam_links.txt"
ANTI_SCAM_WINDOW_SECONDS = 5   # Set to 2 for production, 5 for testing
ANTI_SCAM_CHANNELS = 3         # Number of different channels required

def load_scam_links():
    if not os.path.exists(SCAM_LINKS_FILE):
        return set()
    with open(SCAM_LINKS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_scam_link(link):
    with open(SCAM_LINKS_FILE, "a") as f:
        f.write(link + "\n")

def is_scam_steam_link(content, scam_links):
    steam_regex = r"(https?://[^\s]+)"
    for match in re.findall(steam_regex, content):
        url = match.lower()
        if "steam" in url and not url.startswith("https://store.steampowered.com"):
            if not url.startswith("https://steamcommunity.com"):
                return True, url
        for scam in scam_links:
            if scam in url:
                return True, url
    return False, None

def message_signature(message: discord.Message):
    sig = message.content
    if message.attachments:
        sig += " " + " ".join(a.url for a in message.attachments)
    if message.embeds:
        for e in message.embeds:
            if e.url:
                sig += " " + str(e.url)
            if e.title:
                sig += " " + str(e.title)
    return sig.strip()

def short_uuid(length=5):
    # Use letters and digits
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

class Anti_Scam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)
        self.scam_links = load_scam_links()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
            # ----- New: Check if message is in a DSHERE channel -----
        if "DSHERE" in message.channel.name.upper():  # case-insensitive check
            try:
                # Delete the message
                await message.delete()
                
                # Create a single-use invite in the first text channel
                invite_channel = message.guild.text_channels[0]
                invite = await invite_channel.create_invite(
                    max_age=86400, max_uses=1,
                    reason=f"Invite for {message.author} after DSHERE violation"
                )
    
                # Send the hacked account embed
                embed = discord.Embed(
                    title="⚠️ Possible Account Compromise Detected",
                    description=(
                        f"You were kicked because you sent a message in a protected DSHERE channel.\n"
                        "This is a common sign of a hacked or compromised account.\n\n"
                        "**What you sent:**"
                    ),
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Message Content",
                    value=message.content if len(message.content) < 1024 else message.content[:1000] + "...",
                    inline=False
                )
                embed.add_field(
                    name="How to Secure Your Account",
                    value=(
                        "1. Change your Discord password immediately.\n"
                        "2. Enable 2-Factor Authentication (2FA).\n"
                        "3. Run a malware scan on your computer.\n"
                        "4. Do **not** reuse passwords from other sites."
                    ),
                    inline=False
                )
                embed.add_field(
                    name="Rejoin the Server",
                    value=f"[Click here to rejoin]({invite.url})",
                    inline=False
                )
                embed.set_footer(text="If you believe this was a mistake, contact a server admin.")
    
                await message.author.send(embed=embed)
    
                # Kick the user
                await message.guild.kick(
                    message.author,
                    reason="Sent message in DSHERE channel (protected anti-scam zone)"
                )
    
            except Exception as e:
                print(f"Error handling DSHERE violation: {e}")
            finally:
                # Clear tracked messages for this user to avoid false positives
                self.user_messages[message.author.id].clear()
            return  # Stop processing further

        user_id = message.author.id
        now = time.time()
        sig = message_signature(message)

        # Record the message
        self.user_messages[user_id].append((sig, message.channel.id, now, message))

        # Remove messages older than the window
        self.user_messages[user_id] = [
            (s, ch, ts, msg) for (s, ch, ts, msg) in self.user_messages[user_id] if now - ts <= ANTI_SCAM_WINDOW_SECONDS
        ]

        # Scam link detection as before
        scam_detected, scam_url = is_scam_steam_link(message.content, self.scam_links)
        if scam_detected:
            try:
                await message.delete()
                for member in message.guild.members:
                    if member.guild_permissions.administrator:
                        await member.send(
                            f"⚠️ Possible scam link detected from {message.author.mention} in {message.channel.mention}:\n{scam_url}"
                        )
                        break
                await message.author.send(
                    "⚠️ Your message was removed for containing a suspicious or reported scam link. If you believe this is a mistake, contact an admin."
                )
            except Exception as e:
                print(f"Error handling scam link: {e}")
            return

        # Check for N+ identical messages in N different channels in the window
        sig_msgs = [(s, ch, ts, msg) for (s, ch, ts, msg) in self.user_messages[user_id] if s == sig]
        channels = set(ch for (_, ch, _, _) in sig_msgs)
        if len(channels) >= ANTI_SCAM_CHANNELS:
            channel_to_time = {}
            for (_, ch, ts, _) in sig_msgs:
                if ch not in channel_to_time:
                    channel_to_time[ch] = ts
                if len(channel_to_time) == ANTI_SCAM_CHANNELS:
                    break
            t_earliest = min(channel_to_time.values())
            t_latest = max(channel_to_time.values())
            time_diff = t_latest - t_earliest
            print(f"DEBUG: channels={channels}, time_diff={time_diff}")
            if time_diff <= ANTI_SCAM_WINDOW_SECONDS:
                try:
                    # Delete all matching messages
                    for (_, ch, ts, msg) in sig_msgs:
                        try:
                            await msg.delete()
                        except Exception:
                            pass

                    # Create a single-use invite
                    invite_channel = message.guild.text_channels[0]
                    invite = await invite_channel.create_invite(
                        max_age=86400, max_uses=1,
                        reason=f"Invite for {message.author} after spam/scam detection"
                    )

                    # DM the user
                    embed = discord.Embed(
                        title="⚠️ Possible Account Compromise Detected",
                        description=(
                            f"You were kicked because you sent the **exact same message** in {ANTI_SCAM_CHANNELS} or more channels in a {ANTI_SCAM_WINDOW_SECONDS} second window.\n"
                            "This is a common sign of a hacked or compromised account.\n\n"
                            "**What you sent:**"
                        ),
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Message Content",
                        value=sig if len(sig) < 1024 else sig[:1000] + "...",
                        inline=False
                    )
                    embed.add_field(
                        name="How to Secure Your Account",
                        value=(
                            "1. Change your Discord password immediately.\n"
                            "2. Enable 2-Factor Authentication (2FA).\n"
                            "3. Run a malware scan on your computer.\n"
                            "4. Do **not** reuse passwords from other sites."
                        ),
                        inline=False
                    )
                    embed.add_field(
                        name="Rejoin the Server",
                        value=f"[Click here to rejoin]({invite.url})",
                        inline=False
                    )
                    embed.set_footer(text="If you believe this was a mistake, contact a server admin.")
                    await message.author.send(embed=embed)


                    # Kick the user
                    await message.guild.kick(
                        message.author,
                        reason=f"Possible account compromise: sent identical message in {ANTI_SCAM_CHANNELS}+ channels in {ANTI_SCAM_WINDOW_SECONDS} seconds"
                    )
                except Exception as e:
                    print(f"Error handling mass scam/spam: {e}")
                finally:
                    self.user_messages[user_id].clear()

    @commands.command(name="setupLS")
    @commands.has_permissions(administrator=True)
    async def setupScam(self, ctx):
        randomStr = short_uuid()
        existing_channel = None
        for channel in ctx.guild.text_channels:
            if "DSHERE" in channel.name:
                existing_channel = channel
                break


        try:
            if existing_channel:
                await ctx.send("Failed to create channel.\nError: There's already a DSHERE channel!")
            else:
                channel = await ctx.guild.create_text_channel(f'DSHERE-{randomStr}')
                await channel.send("# WARNING!!!!\nThis channel is intended to be some sort of net to catch scam-bots.\nIf you send a message here we will think you are\nA Robot and we will kick you.")
                await ctx.send("LS Setup is complete!")
        except Exception as e:
            await ctx.send(f'Failed to create channel.\nError: {e}')

    @commands.command(name="report_scam")
    @commands.has_permissions(administrator=True)
    async def report_scam(self, ctx, link: str):
        """Admins can report scam links to the bot."""
        link = link.lower().strip()
        if link in self.scam_links:
            await ctx.send("This link is already reported as a scam.")
            return
        self.scam_links.add(link)
        save_scam_link(link)
        await ctx.send(f"✅ Link `{link}` has been reported as a scam and will be blocked.")

async def setup(bot):
    await bot.add_cog(Anti_Scam(bot))
=======
import discord
from discord.ext import commands
import re
import os
import time
from collections import defaultdict

# === CONFIGURABLE VALUES ===
SCAM_LINKS_FILE = "scam_links.txt"
ANTI_SCAM_WINDOW_SECONDS = 5   # Set to 2 for production, 5 for testing
ANTI_SCAM_CHANNELS = 3         # Number of different channels required

def load_scam_links():
    if not os.path.exists(SCAM_LINKS_FILE):
        return set()
    with open(SCAM_LINKS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_scam_link(link):
    with open(SCAM_LINKS_FILE, "a") as f:
        f.write(link + "\n")

def is_scam_steam_link(content, scam_links):
    steam_regex = r"(https?://[^\s]+)"
    for match in re.findall(steam_regex, content):
        url = match.lower()
        if "steam" in url and not url.startswith("https://store.steampowered.com"):
            if not url.startswith("https://steamcommunity.com"):
                return True, url
        for scam in scam_links:
            if scam in url:
                return True, url
    return False, None

def message_signature(message: discord.Message):
    sig = message.content
    if message.attachments:
        sig += " " + " ".join(a.url for a in message.attachments)
    if message.embeds:
        for e in message.embeds:
            if e.url:
                sig += " " + str(e.url)
            if e.title:
                sig += " " + str(e.title)
    return sig.strip()

class Anti_Scam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)
        self.scam_links = load_scam_links()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id
        now = time.time()
        sig = message_signature(message)

        # Record the message
        self.user_messages[user_id].append((sig, message.channel.id, now, message))

        # Remove messages older than the window
        self.user_messages[user_id] = [
            (s, ch, ts, msg) for (s, ch, ts, msg) in self.user_messages[user_id] if now - ts <= ANTI_SCAM_WINDOW_SECONDS
        ]

        # Scam link detection as before
        scam_detected, scam_url = is_scam_steam_link(message.content, self.scam_links)
        if scam_detected:
            try:
                await message.delete()
                for member in message.guild.members:
                    if member.guild_permissions.administrator:
                        await member.send(
                            f"⚠️ Possible scam link detected from {message.author.mention} in {message.channel.mention}:\n{scam_url}"
                        )
                        break
                await message.author.send(
                    "⚠️ Your message was removed for containing a suspicious or reported scam link. If you believe this is a mistake, contact an admin."
                )
            except Exception as e:
                print(f"Error handling scam link: {e}")
            return

        # Check for N+ identical messages in N different channels in the window
        sig_msgs = [(s, ch, ts, msg) for (s, ch, ts, msg) in self.user_messages[user_id] if s == sig]
        channels = set(ch for (_, ch, _, _) in sig_msgs)
        if len(channels) >= ANTI_SCAM_CHANNELS:
            channel_to_time = {}
            for (_, ch, ts, _) in sig_msgs:
                if ch not in channel_to_time:
                    channel_to_time[ch] = ts
                if len(channel_to_time) == ANTI_SCAM_CHANNELS:
                    break
            t_earliest = min(channel_to_time.values())
            t_latest = max(channel_to_time.values())
            time_diff = t_latest - t_earliest
            print(f"DEBUG: channels={channels}, time_diff={time_diff}")
            if time_diff <= ANTI_SCAM_WINDOW_SECONDS:
                try:
                    # Delete all matching messages
                    for (_, ch, ts, msg) in sig_msgs:
                        try:
                            await msg.delete()
                        except Exception:
                            pass

                    # Create a single-use invite
                    invite_channel = message.guild.text_channels[0]
                    invite = await invite_channel.create_invite(
                        max_age=86400, max_uses=1,
                        reason=f"Invite for {message.author} after spam/scam detection"
                    )

                    # DM the user
                    embed = discord.Embed(
                        title="⚠️ Possible Account Compromise Detected",
                        description=(
                            f"You were kicked because you sent the **exact same message** in {ANTI_SCAM_CHANNELS} or more channels in a {ANTI_SCAM_WINDOW_SECONDS} second window.\n"
                            "This is a common sign of a hacked or compromised account.\n\n"
                            "**What you sent:**"
                        ),
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Message Content",
                        value=sig if len(sig) < 1024 else sig[:1000] + "...",
                        inline=False
                    )
                    embed.add_field(
                        name="How to Secure Your Account",
                        value=(
                            "1. Change your Discord password immediately.\n"
                            "2. Enable 2-Factor Authentication (2FA).\n"
                            "3. Run a malware scan on your computer.\n"
                            "4. Do **not** reuse passwords from other sites."
                        ),
                        inline=False
                    )
                    embed.add_field(
                        name="Rejoin the Server",
                        value=f"[Click here to rejoin]({invite.url})",
                        inline=False
                    )
                    embed.set_footer(text="If you believe this was a mistake, contact a server admin.")
                    await message.author.send(embed=embed)


                    # Kick the user
                    await message.guild.kick(
                        message.author,
                        reason=f"Possible account compromise: sent identical message in {ANTI_SCAM_CHANNELS}+ channels in {ANTI_SCAM_WINDOW_SECONDS} seconds"
                    )
                except Exception as e:
                    print(f"Error handling mass scam/spam: {e}")
                finally:
                    self.user_messages[user_id].clear()

    @commands.command(name="report_scam")
    @commands.has_permissions(administrator=True)
    async def report_scam(self, ctx, link: str):
        """Admins can report scam links to the bot."""
        link = link.lower().strip()
        if link in self.scam_links:
            await ctx.send("This link is already reported as a scam.")
            return
        self.scam_links.add(link)
        save_scam_link(link)
        await ctx.send(f"✅ Link `{link}` has been reported as a scam and will be blocked.")

async def setup(bot):
    await bot.add_cog(Anti_Scam(bot))
>>>>>>> a61aac57848316cddc14a19e8a44ceb462bc0ca7
