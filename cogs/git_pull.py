import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import subprocess
from bot import load_data, save_data


class gitpull(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pull_latest_git", description="Automatically finds the latest GitHub version and updates the bot.")
    async def pull(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        config = load_data("config.json")
        repo_url = config.get("github_repo")
        api_key = config.get("github_api_key")
        admin_roles = config.get("admin_roles", [])
        maintainer_ids = config.get("maintainer_user_id", [])

        # Check user permissions
        is_admin = any(role.id in admin_roles for role in interaction.user.roles) if isinstance(interaction.user, discord.Member) else False
        is_maintainer = interaction.user.id in maintainer_ids

        if not (is_admin or is_maintainer):
            await interaction.followup.send("❌ You do not have permission to use this command.")
            return

        if not repo_url or not api_key:
            await interaction.followup.send("❌ GitHub repo URL or API key missing in config.json.")
            return

        try:
            owner, repo = repo_url.replace("https://github.com/", "").rstrip("/").split("/")
        except:
            await interaction.followup.send("❌ Invalid GitHub repository URL format.")
            return

        headers = {
            "Authorization": f"token {api_key}",
            "Accept": "application/vnd.github+json"
        }

        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/main"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"❌ GitHub API error: {resp.status}")
                    return
                data = await resp.json()

        latest_commit = data.get("sha")
        if not latest_commit:
            await interaction.followup.send("❌ Could not retrieve latest commit.")
            return

        current_data = load_data("last_commit.json")
        current_commit = current_data.get("latest_sha")

        if current_commit == latest_commit:
            await interaction.followup.send("✅ Discord bot is already up-to-date.")
        else:
            result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            save_data("last_commit", {"latest_sha": latest_commit})
            await interaction.followup.send(f"🆕 Bot updated to latest commit!\n```{result.stdout.strip()}```")


async def setup(bot):
    await bot.add_cog(gitpull(bot))
