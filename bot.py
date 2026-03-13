import gspread
from google.oauth2.service_account import Credentials

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("./tmp/service_account.json", scopes=scopes)
clients = gspread.authorize(creds)

obg = clients.open_by_key("1dYo1zlBXFbulieiuVBDmqetOqrw_HRslw0qM-md5Ioo").sheet1
data_obg = obg.get('A2:E')
headers = data_obg[0]
data_obg = [dict(zip(headers, row)) for row in data_obg[1:]]
data_obg = {(i['Song Name'], i['Difficulty']): i for i in data_obg}

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)


    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

@bot.tree.command(name="obg_const", description="Get song details")
async def obg_const(interaction: discord.Interaction, song: str, difficulty: str = 'Master'):
    entry = data_obg.get((song, difficulty))
    
    if not entry:
        await interaction.response.send_message("Song not found!", ephemeral=True)
        return

    embed = discord.Embed(
        title=entry['Song Name'],
        description=f"**Difficulty:** {entry['Difficulty']}\n"
                    f"**Level:** `{entry['Ingame Constant']}`\n"
                    f"**FC Constant:** `{entry['FC Constant']}`\n"
                    f"**AP Constant:** `{entry['AP Constant']}`\n"
                    f"**Source:** `OBG opinion list`"
    )

    await interaction.response.send_message(embed=embed)
    @tasks.loop(minutes=30)
    async def refresh_sheet_data_obg(self):
        global data_obg
        print("Fetching fresh data_obg from Google Sheets...")
        
        try:
            obg = clients.open_by_key("1dYo1zlBXFbulieiuVBDmqetOqrw_HRslw0qM-md5Ioo").sheet1
            raw_data_obg = obg.get('A2:E')
            
            if raw_data_obg:
                headers = raw_data_obg[0]
                parsed = [dict(zip(headers, row)) for row in raw_data_obg[1:]]
                
                data_obg = {(i['Song Name'], i['Difficulty']): i for i in parsed}
                print(f"Successfully cached {len(data_obg)} songs!")
                
        except Exception as e:
            print(f"Failed to update data_obg: {e}")

    @refresh_sheet_data_obg.before_loop
    async def before_refresh(self):
        await self.wait_until_ready()

@obg_const.autocomplete('song')
async def song_autocomplete(interaction: discord.Interaction, current: str):
    unique_songs = sorted(list(set(name for name, diff in data_obg.keys())))
    return [
        app_commands.Choice(name=s, value=s)
        for s in unique_songs if current.lower() in s.lower()
    ][:10]

@obg_const.autocomplete('difficulty')
async def diff_autocomplete(interaction: discord.Interaction, current: str):
    chosen_song = interaction.namespace.song
    
    available_diffs = [
        diff for name, diff in data_obg.keys() 
        if name.lower() == (chosen_song or "").lower()
    ]
    
    return [
        app_commands.Choice(name=d.title(), value=d)
        for d in available_diffs if current.lower() in d.lower()
    ]

bot.run(TOKEN)