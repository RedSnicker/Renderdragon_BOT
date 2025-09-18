import discord
from discord.ext import commands
from collections import defaultdict

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_warnings = defaultdict(list)  # {user_id: [reasons]}

    async def resolve_member(self, ctx, user_str):
        user_id = None
        if user_str.isdigit():
            user_id = int(user_str)
        elif user_str.startswith("<@") and user_str.endswith(">"):
            user_id = int(user_str.replace("<@", "").replace("!", "").replace(">", ""))
        if user_id:
            member = ctx.guild.get_member(user_id)
            if member:
                return member

        user_str_lower = user_str.lower()
        for member in ctx.guild.members:
            if (
                member.name.lower() == user_str_lower or
                (member.nick and member.nick.lower() == user_str_lower) or
                (hasattr(member, "display_name") and member.display_name.lower() == user_str_lower)
            ):
                return member

        return None

    @commands.hybrid_command(name="warn")
    async def warn(self, ctx, user: str, *, reason: str = "No reason provided."):
        member = await self.resolve_member(ctx, user)
        if not member:
            await ctx.send(f"Could not find user `{user}`.")
            return
        self.user_warnings[member.id].append(reason)
        await ctx.send(f"Warned {member.mention} for: {reason}")
        try:
            await member.send(f"You have been warned in **{ctx.guild.name}** for: {reason}")
        except Exception:
            pass

    @commands.hybrid_command(name="clearwarn")
    async def clearwarn(self, ctx, user: str):
        member = await self.resolve_member(ctx, user)
        if not member:
            await ctx.send(f"Could not find user `{user}`.")
            return
        if self.user_warnings.get(member.id):
            self.user_warnings[member.id].clear()
            await ctx.send(f"All warnings cleared for {member.mention}.")
        else:
            await ctx.send(f"{member.mention} has no warnings to clear.")

    @commands.hybrid_command(name="warns")
    async def warnings(self, ctx, user: str = None):
        if user:
            member = await self.resolve_member(ctx, user)
            if not member:
                await ctx.send(f"Could not find user `{user}`.")
                return
        else:
            member = ctx.author
        warnings = self.user_warnings.get(member.id, [])
        if not warnings:
            await ctx.send(f"{member.mention} has no warnings.")
        else:
            warning_list = "\n".join(f"{i+1}. {w}" for i, w in enumerate(warnings))
            await ctx.send(f"Warnings for {member.mention}:\n{warning_list}")

async def setup(bot):
    await bot.add_cog(Warn(bot))