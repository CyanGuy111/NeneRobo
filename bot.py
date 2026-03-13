import gspread
from google.oauth2.service_account import Credentials
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
import os
from dotenv import load_dotenv

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
clients = gspread.authorize(creds)

data = {}

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
        self.refresh_sheet_data.start()

    @tasks.loop(minutes=15)
    async def refresh_sheet_data(self):
        global data
        print("Fetching fresh data from Google Sheets...")
        
        try:
            obg = clients.open_by_key("1dYo1zlBXFbulieiuVBDmqetOqrw_HRslw0qM-md5Ioo").sheet1
            raw_data = obg.get('A2:F')
            
            if raw_data:
                headers = raw_data[0]
                parsed = [dict(zip(headers, row)) for row in raw_data[1:]]
                
                data = {(i['ID'], i['Difficulty']): i for i in parsed}
                print(f"Successfully cached OBG")
                
        except Exception as e:
            print(f"Failed to update data (OBG): {e}")

        try:
            s39s = clients.open_by_key("1B8tX9VL2PcSJKyuHFVd2UT_8kYlY4ZdwHwg9MfWOPug").worksheet('Constants')
            raw_data = s39s.get('A:G')
            
            if raw_data:
                headers = raw_data[0]
                parsed = [dict(zip(headers, row)) for row in raw_data[1:]]
                
                for i in parsed:
                    if (i['Song ID'], i['Difficulty']) in data:
                        data[(i['Song ID'], i['Difficulty'])]["Japanese name"] = i[""]
                        data[(i['Song ID'], i['Difficulty'])]["39s const"] = i["Constant"]
                print(f"Successfully cached 39s")
                
        except Exception as e:
            print(f"Failed to update data (39s): {e}")

    @refresh_sheet_data.before_loop
    async def before_refresh(self):
        await self.wait_until_ready()

bot = MyBot()

def get_img_url(song_id):
    return f"https://storage.sekai.best/sekai-jp-assets/music/jacket/jacket_s_" + f"{song_id:0>{3}}" + f"/jacket_s_" + f"{song_id:0>{3}}" + f".webp"

async def song_autocomplete(interaction: discord.Interaction, current: str):
    unique_songs = sorted(list(set(info.get('Song Name', '') for info in data.values() if info.get('Song Name'))))
    return [
        app_commands.Choice(name=s, value=s)
        for s in unique_songs if current.lower() in s.lower()
    ][:10]

async def diff_autocomplete(interaction: discord.Interaction, current: str):
    # Safely check if the current command even has a 'song' parameter typed in
    chosen_song = getattr(interaction.namespace, 'song', None)
    
    available_diffs = [
        info.get('Difficulty', '') for info in data.values() 
        if info.get('Song Name', '').lower() == (chosen_song or "").lower()
    ]
    
    return [
        app_commands.Choice(name=d.title(), value=d)
        for d in available_diffs if current.lower() in d.lower()
    ][:10]

@bot.tree.command(name="song_constant", description="Get song details")
@app_commands.autocomplete(song=song_autocomplete, difficulty=diff_autocomplete)
async def song_constant(interaction: discord.Interaction, song: str, difficulty: str = 'Master'):
    entry = None
    
    for info in data.values():
        if info.get('Song Name', '').lower() == song.lower() and info.get('Difficulty', '').lower() == difficulty.lower():
            entry = info
            break
    
    if not entry:
        await interaction.response.send_message("Song not found!", ephemeral=True)
        return

    FC_const = entry.get('FC Constant', 'N/A')
    AP_const = entry.get('AP Constant', 'N/A')
    jp_name = entry.get('Japanese name', 'N/A')

    embed = discord.Embed(
        title=entry.get('Song Name', 'Unknown'),
        description=f"**Difficulty:** {entry.get('Difficulty', 'Unknown')}\n"
                    f"**JP name:** `{jp_name if jp_name != '' else 'N/A'}`\n"
                    f"**Level:** `{entry.get('Ingame Constant', 'N/A')}`\n"
                    f"**FC Constant (OBG list):** `{FC_const if FC_const != '0.0' else 'N/A'}`\n"
                    f"**AP Constant (OBG list):** `{AP_const if AP_const != '0.0' else 'N/A'}`\n"
                    f"**39s Constant:** `{entry.get('39s const', 'N/A')}`\n"
    )
    embed.set_thumbnail(url=get_img_url(int(entry.get('ID', 'N/A'))))  
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="get_jacket", description="Get song jacket")
@app_commands.autocomplete(song=song_autocomplete)
async def get_jacket(interaction: discord.Interaction, song: str):
    entry = None
    
    for info in data.values():
        if info.get('Song Name', '').lower() == song.lower() and info.get('Difficulty', '').lower() == 'master':
            entry = info
            break
    
    if not entry:
        await interaction.response.send_message("Song not found!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=entry.get('Song Name', 'Unknown'),
    )
    embed.set_image(url=get_img_url(int(entry.get('ID', 'N/A'))))  
    await interaction.response.send_message(embed=embed)
bot.run(TOKEN)