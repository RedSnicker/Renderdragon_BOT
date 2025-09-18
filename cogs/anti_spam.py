import discord
from discord.ext import commands
import time
from collections import defaultdict
from datetime import timedelta
import asyncio

class Anti_Spam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)

    async def safe_bulk_delete(self, channel, messages):
        for i in range(0, len(messages), 100):
            chunk = messages[i:i+100]
            while True:
                try:
                    await channel.delete_messages(chunk)
                    break
                except discord.errors.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        retry_after = getattr(e, "retry_after", 2)
                        await asyncio.sleep(retry_after)
                    else:
                        for m in chunk:
                            try:
                                await m.delete()
                            except Exception:
                                pass
                        break

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = message.author.id
        now = time.time()

        self.user_messages[user_id].append((now, message))
        self.user_messages[user_id] = [
            (ts, msg) for ts, msg in self.user_messages[user_id] if now - ts <= 5
        ]

        if len(self.user_messages[user_id]) >= 5:
            spam_messages = [msg_obj for _, msg_obj in self.user_messages[user_id]]

            try:
                # Use discord.utils.utcnow() for aware datetime
                until = discord.utils.utcnow() + timedelta(seconds=20)
                await message.author.timeout(until, reason="Spamming 5+ messages in 5 seconds")
            except Exception as e:
                print(f"Failed to timeout user: {e}")

            try:
                embed = discord.Embed(
                    title="⚠️ Spam Warning",
                    description=(
                        "You sent 5 or more messages in 5 seconds. "
                        "You have been timed out for 20 seconds. Please avoid spamming."
                    ),
                    color=discord.Color.orange()
                )
                await message.author.send(embed=embed)
            except Exception:
                pass

            warning_cog = self.bot.get_cog("WarningS")
            if warning_cog:
                await warning_cog.warn(message.author, "Spamming 10+ messages in 5 seconds.")

            channel_message_map = defaultdict(list)
            for msg in spam_messages:
                channel_message_map[msg.channel].append(msg)

            for channel, msgs in channel_message_map.items():
                deletable_msgs = [
                    m for m in msgs
                    if (time.time() - m.created_at.timestamp() < 60*60*24*14) and not m.is_system()
                ]
                if deletable_msgs:
                    await self.safe_bulk_delete(channel, deletable_msgs)

            self.user_messages[user_id].clear()

async def setup(bot):
    await bot.add_cog(Anti_Spam(bot))