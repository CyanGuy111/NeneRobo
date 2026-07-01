import os
import subprocess
import sys

import discord
from discord import app_commands

from config import BOT_SERVER_ID
from utils import is_admin, is_owner
from jacket_fetch import download_jackets


def register_admin_commands(bot):

    @bot.tree.command(name="sync-database", description="Force the bot to sync with the spreadsheet")
    @is_admin()
    async def force_update(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.client.fetch_data()
        download_jackets()
        await interaction.followup.send("Update complete!")

    @force_update.error
    async def force_update_error(interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You do not have permission to use this command.")

    @bot.tree.command(
        name="update-bot",
        description="Call git pull, update dependencies, and restart bot",
        guild=discord.Object(id=BOT_SERVER_ID) if BOT_SERVER_ID else None
    )
    @is_owner()
    async def update_bot(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            git_process = subprocess.run(
                ['git', 'pull'],
                capture_output=True,
                text=True,
                check=True
            )
            if 'requirements.txt' in git_process.stdout:
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                    capture_output=True,
                    check=True
                )

            await interaction.followup.send("Updated. Restarting...")

            os.execv(sys.executable, [sys.executable] + sys.argv)

        except subprocess.CalledProcessError as e:
            err_msg = e.stderr or e.stdout
            await interaction.followup.send(f"Command error: `{err_msg[-1900:]}`")
        except Exception as e:
            await interaction.followup.send(f"Error: `{e}`")

    @update_bot.error
    async def update_bot_error(interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("You do not have permission to use this command.")