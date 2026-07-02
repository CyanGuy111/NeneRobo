import discord
from discord.ext import commands, tasks

from config import get_intents, BOT_SERVER_ID
from db import ScoreDatabase
from sheets import fetch_song_data
from aliases import load_aliases
from romaji import load_romaji_cache, refresh_romaji


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=get_intents())
        self.data = {}
        self.unique_songs = []
        self._base_normalized_names = []
        self.name_lookup = {}
        self.alias_map = load_aliases()
        self.romaji_map = load_romaji_cache()
        self.db = ScoreDatabase()

    async def setup_hook(self):
        await self.db.connect()

        await self.tree.sync()

        if BOT_SERVER_ID != 0:
            bot_server = discord.Object(id=BOT_SERVER_ID)
            await self.tree.sync(guild=bot_server)

        print(f"Synced slash commands for {self.user}")
        self.refresh_sheet_data.start()
        self.refresh_romaji_data.start()

    async def close(self):
        await self.db.close()
        await super().close()

    @tasks.loop(minutes=15)
    async def refresh_sheet_data(self):
        await self.fetch_data()

    @refresh_sheet_data.before_loop
    async def before_refresh(self):
        await self.wait_until_ready()

    @tasks.loop(hours=24)
    async def refresh_romaji_data(self):
        try:
            self.romaji_map = await refresh_romaji()
            self._rebuild_name_lookup()
            print(f"Refreshed romaji data ({len(self.romaji_map)} songs)")
        except Exception as e:
            print(f"Failed to refresh romaji data, keeping existing cache: {e}")

    @refresh_romaji_data.before_loop
    async def before_romaji_refresh(self):
        await self.wait_until_ready()

    async def fetch_data(self):
        self.data, self.unique_songs, self._base_normalized_names = await fetch_song_data()
        self._rebuild_name_lookup()

        try:
            await self.db.sync_constants(self.data)
            print("Sync the score database successfully")
        except Exception as e:
            print(f"Failed to sync the score database. {e}")

        print("Syncing completed.")

    def _rebuild_name_lookup(self):
        lookup = {}

        for norm, name in self._base_normalized_names:
            lookup[norm] = name

        for norm_alias, canonical in self.alias_map.items():
            if canonical in self.unique_songs:
                lookup.setdefault(norm_alias, canonical)

        if self.romaji_map:
            for info in self.data.values():
                song_id = str(info.get('ID', ''))
                romaji = self.romaji_map.get(song_id)
                song_name = info.get('Song Name')

                if romaji and song_name:
                    info['Romaji'] = romaji
                    lookup.setdefault("".join(romaji.lower().split()), song_name)

        self.name_lookup = lookup


bot = MyBot()