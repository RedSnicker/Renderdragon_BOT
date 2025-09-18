import discord
from discord.ext import commands
import re
import os
import aiohttp
from datetime import timedelta
import json

MODLOG_CHANNEL_FILE = "modlog_channel.txt"
NSFW_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".mp4", ".mov", ".avi", ".webm"}

NSFW_KEYWORDS = [
    "porn", "sex", "nude", "xxx", "hentai", "nsfw", "boobs", "dick", "cock", "pussy",
    "cum", "anal", "blowjob", "fap", "milf", "naked", "tits", "ass", "b00bs", "b!tch",
    "slut", "vagina", "penis", "orgasm", "masturbate", "jerk off", "suck", "deepthroat",
    "69", "threesome", "bdsm", "fetish", "hardcore", "incest", "creampie", "p0rn", "p*rn"
]

def contains_nsfw(content):
    content_lower = content.lower()
    for word in NSFW_KEYWORDS:
        if word.isalpha():
            pattern = r'\b' + re.escape(word) + r'\b'
        else:
            pattern = re.escape(word)
        if re.search(pattern, content_lower):
            return True
    return False

def save_modlog_channel(channel_id):
    with open(MODLOG_CHANNEL_FILE, "w") as f:
        f.write(str(channel_id))

def load_modlog_channel():
    if not os.path.exists(MODLOG_CHANNEL_FILE):
        return None
    with open(MODLOG_CHANNEL_FILE, "r") as f:
        return int(f.read().strip())

def is_nsfw_from_api(nudity: dict, recreational_drug: dict, gore: dict, tobacco: dict, gambling: dict, minors: dict, ai: dict) -> bool:
    # Only flag as NSFW if any of these are extremely high
    return (
        nudity.get('sexual_activity', 0) >= 0.98 or
        nudity.get('sexual_display', 0) >= 0.98 or
        nudity.get('erotica', 0) >= 0.98 or
        recreational_drug.get("prob", 0) >= 0.98 or
        minors.get('minor', None) or
        ai.get("prob", 0) >= 0.98 or
        gore.get("prob", 0) >= 0.98 or
        tobacco.get("prob", 0) >= 0.98 or
        gambling.get("prob", 0) >= 0.98
    )

class Anti_NSFW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_nsfw_image(self, url):
        params = {
            'url': url,
            'models': 'nudity-2.1,recreational_drug,medical,scam,face-attributes,gore-2.0,qr-content,tobacco,violence,self-harm,money,gambling',
            'api_user': '55796118',
            'api_secret': 'wK4dxV2CtCGRRZLVX9Zuc3XZbUNWBhiY'
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://api.sightengine.com/1.0/check.json', params=params) as resp:
                    data = await resp.json()
                    return data
            except Exception as e:
                print(f"Sightengine API error: {e}")
                return None

    async def process_nsfw(self, message, reason, api_data=None):
        try:
            until = discord.utils.utcnow() + timedelta(seconds=20)
            await message.author.timeout(until, reason=reason)
        except Exception as e:
            print(f"Failed to timeout user: {e}")

        try:
            await message.delete()
            embed = discord.Embed(
                title="⚠️ Inappropriate Warning",
                description=(
                    f"You sent an inappropriate or NSFW message ({reason}). "
                    "You have been timed out for 20 seconds. Please avoid sending NSFW content."
                ),
                color=discord.Color.orange()
            )
            if message.content:
                embed.add_field(name="Your Message:", value=discord.utils.escape_markdown(message.content), inline=False)
            if message.attachments:
                embed.add_field(name="Attachment(s):", value="\n".join(a.url for a in message.attachments), inline=False)
            if api_data:
                embed.add_field(name="Detection Details", value=f"```json\n{json.dumps(api_data, indent=2)[:900]}\n```", inline=False)
            await message.author.send(embed=embed)
        except Exception as e:
            print(f"Error deleting NSFW message: {e}")

        modlog_channel_id = load_modlog_channel()
        if modlog_channel_id:
            modlog_channel = self.bot.get_channel(modlog_channel_id)
            if modlog_channel:
                mod_embed = discord.Embed(
                    title="🚨 NSFW/INAPPROPRIATE MESSAGE DETECTED",
                    description=f"User: {message.author.mention} (`{message.author.id}`)\nChannel: {message.channel.mention}",
                    color=discord.Color.red()
                )
                if message.content:
                    mod_embed.add_field(name="Message Content", value=discord.utils.escape_markdown(message.content), inline=False)
                if message.attachments:
                    mod_embed.add_field(name="Attachment(s):", value="\n".join(a.url for a in message.attachments), inline=False)
                if api_data:
                    mod_embed.add_field(name="Detection Details", value=f"```json\n{json.dumps(api_data, indent=2)[:900]}\n```", inline=False)
                mod_embed.timestamp = discord.utils.utcnow()
                await modlog_channel.send(embed=mod_embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Text NSFW detection
        if contains_nsfw(message.content):
            await self.process_nsfw(message, "NSFW text")
            return

        # Image NSFW detection (Sightengine API)
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                api_data = await self.is_nsfw_image(attachment.url)
                if api_data:
                    # Always send API results
                    #await self.send_api_results(message, api_data)
                    nudity = api_data.get('nudity', {})
                    drugs = api_data.get('recreational_drugs', {})
                    gore = api_data.get('gore', {})
                    cigarrette = api_data.get('tobacco', {})
                    gambling = api_data.get('gambling', {})
                    faces = api_data.get('faces') or [{}]
                    minors = faces[0].get('attributes', {})
                    ai = api_data.get('type', {})
                    if is_nsfw_from_api(nudity,drugs,gore,cigarrette,gambling,minors,ai):
                        await self.process_nsfw(message, "NSFW image (Sightengine AI detected)", api_data)
                else:
                    # If API fails, fallback to filename/extension check
                    filename = attachment.filename.lower()
                    if any(word in filename for word in NSFW_KEYWORDS) or any(filename.endswith(ext) for ext in NSFW_IMAGE_EXTENSIONS):
                        await self.process_nsfw(message, "NSFW image/attachment (filename/extension)")
                return  # Only process the first image attachment!

    @commands.command(name="set_modlog")
    @commands.has_permissions(administrator=True)
    async def set_modlog(self, ctx, channel: discord.TextChannel):
        """Set the mod log channel for NSFW/inappropriate message logs."""
        save_modlog_channel(channel.id)
        await ctx.send(f"✅ Mod log channel set to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Anti_NSFW(bot))