import discord
from discord.ext import commands
import requests
from io import BytesIO
from PIL import Image
import base64
import json

class Minecraft_Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Slow down! Try again in `{error.retry_after:.2f}` seconds.")

    ##########################################################################################

    @commands.hybrid_command(name="minecraft_get_skin")
    async def get_skin(self, ctx: commands.Context, name: str):
        uuid_resp = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}")
        if uuid_resp.status_code != 200:
            await ctx.send("❌ Username not found.")
            return

        uuid_data = uuid_resp.json()
        uuid_str = uuid_data['id']
        profile_resp = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid_str}")
        encoded = profile_resp.json()["properties"][0]["value"]
        skin_data = json.loads(base64.b64decode(encoded).decode())
        skin_url = skin_data["textures"]["SKIN"]["url"]

        await ctx.send(f"{skin_url}")

    ########

    @commands.hybrid_command(name="minecraft_get_uuid")
    async def get_uuid(self, ctx: commands.Context, name: str):
        uuid_resp = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}")
        if uuid_resp.status_code != 200:
            await ctx.send("❌ Username not found.")
            return

        uuid_data = uuid_resp.json()
        uuid_str = uuid_data['id']

        await ctx.send(f"{uuid_str}")

    #######

    @commands.hybrid_command(name="minecraft_get_name")
    async def get_name(self, ctx: commands.Context, uuid: str):
        name_resp = requests.get(f"https://api.minecraftservices.com/minecraft/profile/lookup/{uuid}")
        if name_resp.status_code != 200:
            await ctx.send("❌ UUID is incorrect.")
            return

        name_data = name_resp.json()
        name_str = name_data['name']

        await ctx.send(f"{name_str}")

    #######
    
    @commands.hybrid_command(name="minecraft_render_body")
    async def render_body(self, ctx: commands.Context, name: str):
        def get_average_color(image_bytes):
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            pixels = list(img.getdata())
            avg_color = tuple(sum(c) // len(c) for c in zip(*pixels))
            return discord.Color.from_rgb(*avg_color)

        await ctx.defer()

        # Get UUID from Mojang
        uuid_resp = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{name}")
        if uuid_resp.status_code != 200:
            await ctx.send("❌ Username not found.")
            return

        uuid_data = uuid_resp.json()
        uuid_str = uuid_data['id']

        # Crafatar render URLs
        body_url = f"https://crafatar.com/renders/body/{uuid_str}?size=512&default=MHF_Alex&overlay"
        head_url = f"https://crafatar.com/avatars/{uuid_str}?size=128&overlay"

        # Download both images
        body_resp = requests.get(body_url)
        head_resp = requests.get(head_url)

        if body_resp.status_code != 200 or head_resp.status_code != 200:
            await ctx.send("❌ Failed to get skin render.")
            return

        body_bytes = body_resp.content
        head_bytes = head_resp.content
        avg_color = get_average_color(body_bytes)

        # Prepare in-memory files
        body_file = discord.File(BytesIO(body_bytes), filename=f"{name}_body.png")
        head_file = discord.File(BytesIO(head_bytes), filename=f"{name}_head.png")

        # Build embed
        embed = discord.Embed(
            title=f"{name}'s Minecraft Skin",
            description="Full body with 3D head preview",
            color=avg_color
        )
        embed.set_image(url=f"attachment://{name}_body.png")
        embed.set_thumbnail(url=f"attachment://{name}_head.png")

        await ctx.send(embed=embed, files=[body_file, head_file])



async def setup(bot):
    await bot.add_cog(Minecraft_Utils(bot))