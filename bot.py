import discord
from discord.ext import commands, tasks

from config import get_intents, BOT_SERVER_ID
from db import ScoreDatabase
from sheets import fetch_song_data


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=get_intents())
        self.data = {}
        self.unique_songs = []
        self._normalized_names = []
        self.db = ScoreDatabase()

    async def setup_hook(self):
        await self.db.connect()

        await self.tree.sync()

        if BOT_SERVER_ID != 0:
            bot_server = discord.Object(id=BOT_SERVER_ID)
            await self.tree.sync(guild=bot_server)

        print(f"Synced slash commands for {self.user}")
        self.refresh_sheet_data.start()

    async def close(self):
        await self.db.close()
        await super().close()

    @tasks.loop(minutes=15)
    async def refresh_sheet_data(self):
        await self.fetch_data()

    @refresh_sheet_data.before_loop
    async def before_refresh(self):
        await self.wait_until_ready()

    async def fetch_data(self):
        self.data, self.unique_songs, self._normalized_names = await fetch_song_data()

        try:
            await self.db.sync_constants(self.data)
            print("Sync the score database successfully")
        except Exception as e:
            print(f"Failed to sync the score database. {e}")

        print("Syncing completed.")

bot = MyBot()