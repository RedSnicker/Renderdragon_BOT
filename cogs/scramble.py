import discord.ext

class Scramble(discord.ext.commands.Cog):
    def __init__(self, bot, key):
        self.bot = bot
        self.key = key

    def to_scrambled(self, text, key):
        return key + text[::2] + text[1::2]

    def from_scrambled_to_original(self, scrambled, key):
        scrambled = scrambled.replace(key, "", 1)
        scrambled = scrambled.replace("Scrambled: ", "", 1)
        scrambled = scrambled.replace(f", Key: {key}", "")

        lines = (len(scrambled) + 1) // 2
        part1 = scrambled[:lines]
        part2 = scrambled[lines:]
        original_text = ''.join(a + b for a, b in zip(part1, part2))
        if len(part1) > len(part2): return original_text + part1[-1]
        return original_text

    @discord.ext.commands.hybrid_command(name="scramble", description="Scramble Text")
    @discord.app_commands.allowed_contexts(True, True, True)
    async def scrambleText(self, ctx: discord.ext.commands.Context, times=1, *, text: str, key=None):
        if key is None: key = self.key

        current_text = text

        for _ in range(times):
            current_text = self.to_scrambled(current_text, key)

        if len(f"Scrambled: {current_text}, Key: {key}") <= 2000:
            await ctx.send(f"Scrambled: {current_text}, Key: {key}")
        else:
            await ctx.send(f"Error Scrambling: Message too long")

    @discord.ext.commands.hybrid_command(name="unscramble", description="Unscramble Text")
    @discord.app_commands.allowed_contexts(True, True, True)
    async def unScrambleText(self, ctx: discord.ext.commands.Context, times=1, *, text: str, key=None):
        if key is None: key = self.key

        current_text = text

        for _ in range(times):
            current_text = self.from_scrambled_to_original(current_text, key)

        if len(f"Unscrambled: {current_text}") <= 2000:
            await ctx.send(f"Unscrambled: {current_text}")
        else:
            await ctx.send(f"Error Unscrambling: Message too long")


async def setup(bot):
    await bot.add_cog(Scramble(bot, "SB8711HGhkgj"))