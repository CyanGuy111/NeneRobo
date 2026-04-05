import os
import requests
from dotenv import load_dotenv
import random
from typing import Literal
import aiosqlite
import asyncio

import gspread
from google.oauth2.service_account import Credentials

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks

from image_gen import generate_b30_image
from jacket_fetch import download_jackets

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
clients = gspread.authorize(creds)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

def is_admin():
    def check(interaction: discord.Interaction) -> bool:
        admins = [int(i) for i in os.getenv("ADMIN_IDs").split(',')]
        return interaction.user.id in admins
    return app_commands.check(check)

def get_b30_const(c_39, obg_const, ingame_const):
    if c_39 and str(c_39).strip() not in ['N/A', '', '0.0', '0']:
        return float(c_39)
    
    try:
        obg_val = float(obg_const) if obg_const and str(obg_const).strip() not in ['N/A', ''] else 0.0
        game_val = float(ingame_const) if ingame_const and str(ingame_const).strip() not in ['N/A', ''] else 0.0
    except ValueError:
        return 0.0
    
    if obg_val == 0.0:
        return game_val
    
    if int(obg_val) < int(game_val):
        return float(f"{int(game_val)}.0")
    elif int(obg_val) > int(game_val):
        return float(f"{int(game_val)}.9")
    else:
        return obg_val

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.data = {}

    async def setup_hook(self):
        self.db = await aiosqlite.connect('scores.db')
        
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS user_scores (
                user_id INTEGER,
                song_id TEXT,
                difficulty TEXT,
                constant REAL,
                clear_type TEXT,
                UNIQUE(user_id, song_id, difficulty)
            )
        ''')
        await self.db.commit()

        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")
        self.refresh_sheet_data.start()

    async def update_score(self, records: list[tuple]):
        if not records:
            return
        
        await self.db.executemany('''
            INSERT OR REPLACE INTO user_scores (user_id, song_id, difficulty, constant, clear_type)
            VALUES (?, ?, ?, ?, ?)
        ''', records)

        await self.db.commit()

    async def remove_score(self, user_id: int, song_id: str, difficulty: str) -> int:
        async with self.db.execute('''
            DELETE FROM user_scores 
            WHERE user_id = ? AND song_id = ? AND difficulty = ?
        ''', (user_id, song_id, difficulty)) as cursor:
            deleted_rows = cursor.rowcount
            
        await self.db.commit()
        return deleted_rows

    @tasks.loop(minutes=15)
    async def refresh_sheet_data(self):
        await self.fetch_data()

    @refresh_sheet_data.before_loop
    async def before_refresh(self):
        await self.wait_until_ready()

    async def sync_db(self):
        async with self.db.execute('SELECT user_id, song_id, difficulty, clear_type FROM user_scores') as cursor:
            all_scores = await cursor.fetchall()
            
        update_batch = []
        
        for user_id, song_id, difficulty, clear_type in all_scores:
            song_info = self.data.get((song_id, difficulty))
            
            if song_info:
                c_39 = song_info.get('39s const')
                c_game = song_info['Ingame Constant']

                c_39 = float(c_39) if c_39 and c_39 not in ['N/A', ''] else None
                c_game = float(c_game) if c_game and c_game not in ['N/A', ''] else 0.0

                if clear_type == 'AP':
                    obg_const = song_info.get('AP Constant')
                else:
                    obg_const = song_info.get('FC Constant')

                const = get_b30_const(c_39, obg_const, c_game)
                update_batch.append((const, user_id, song_id, difficulty))
                
        if update_batch:
            await self.db.executemany('''
                UPDATE user_scores 
                SET constant = ? 
                WHERE user_id = ? AND song_id = ? AND difficulty = ?
            ''', update_batch)
            await self.db.commit()
        
    async def fetch_data(self):
        print("Fetching fresh data from Google Sheets...")

        def fetch_obg():
            return clients.open_by_key("1dYo1zlBXFbulieiuVBDmqetOqrw_HRslw0qM-md5Ioo").sheet1.get_all_values()
        
        def fetch_39s():
            return clients.open_by_key("1B8tX9VL2PcSJKyuHFVd2UT_8kYlY4ZdwHwg9MfWOPug").worksheet('Constants').get('A:G')
        
        try:
            raw_data = await asyncio.to_thread(fetch_obg)
            
            if raw_data:
                headers = raw_data[1][:6] + ['Notes']
                parsed = []
                
                for row in raw_data[2:]:
                    if not row:
                        continue
                    
                    padded_row = row + ([""] * (17 - len(row)))

                    parsed.append(dict(zip(headers, padded_row[:6] + [padded_row[-1]])))

                self.data = {(i['ID'], i['Difficulty']): i for i in parsed}
                self.unique_songs = sorted(list(set(info.get('Song Name', '') for info in self.data.values() if info.get('Song Name'))))

                print(f"Successfully cached OBG")
                
        except Exception as e:
            print(f"Failed to update data (OBG): {e}")

        try:
            raw_data = await asyncio.to_thread(fetch_39s)
            
            if raw_data:
                headers = raw_data[0]
                parsed = [dict(zip(headers, row)) for row in raw_data[1:]]
                
                for i in parsed:
                    if (i['Song ID'], i['Difficulty']) in self.data:
                        self.data[(i['Song ID'], i['Difficulty'])]["Japanese name"] = i[""]
                        self.data[(i['Song ID'], i['Difficulty'])]["39s const"] = i["Constant"]
                print(f"Successfully cached 39s")
                
        except Exception as e:
            print(f"Failed to update data (39s): {e}")

        try:
            await self.sync_db() 
            print(f"Sync the score database successfully")
        except Exception as e:
            print(f"Failed to sync the score database. {e}")

        print("Syncing completed.")

bot = MyBot()

def get_img_url(song_id):
    jp_url = f"https://storage.sekai.best/sekai-jp-assets/music/jacket/jacket_s_{song_id:03}/jacket_s_{song_id:03}.webp"
    en_url = f"https://storage.sekai.best/sekai-en-assets/music/jacket/jacket_s_{song_id:03}/jacket_s_{song_id:03}.webp"

    try:
        response = requests.head(jp_url, timeout=5)
        if response.status_code == 200:
            return jp_url
    except requests.RequestException:
        pass
        
    return en_url

async def song_autocomplete(interaction: discord.Interaction, current: str):
    unique_songs = getattr(interaction.client, 'unique_songs', [])
    return [
        app_commands.Choice(name=s, value=s)
        for s in unique_songs if current.lower() in s.lower()
    ][:10]

async def diff_autocomplete(interaction: discord.Interaction, current: str):
    # Safely check if the current command even has a 'song' parameter typed in
    chosen_song = getattr(interaction.namespace, 'song', None)
    
    available_diffs = [
        info.get('Difficulty', '') for info in interaction.client.data.values() 
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
    
    for info in interaction.client.data.values():
        if info.get('Song Name', '').lower() == song.lower() and info.get('Difficulty', '').lower() == difficulty.lower():
            entry = info
            break
    
    if not entry:
        await interaction.response.send_message("Song not found!", ephemeral=True)
        return

    FC_const = entry.get('FC Constant', 'N/A')
    AP_const = entry.get('AP Constant', 'N/A')
    jp_name = entry.get('Japanese name', 'N/A')
    note = f"**Note:** `{entry.get('Notes')}`" if entry.get('Notes') else ""

    embed = discord.Embed(
        title=entry.get('Song Name', 'Unknown'),
        description=f"**Difficulty:** {entry.get('Difficulty', 'Unknown')}\n"
                    f"**JP name:** `{jp_name if jp_name != '' else 'N/A'}`\n"
                    f"**Level:** `{entry.get('Ingame Constant', 'N/A')}`\n"
                    f"**39s Constant:** `{entry.get('39s const', 'N/A')}`\n"
                    f"**FC Constant (OBG list):** `{FC_const if FC_const != '0.0' else 'N/A'}`\n"
                    f"**AP Constant (OBG list):** `{AP_const if AP_const != '0.0' else 'N/A'}`\n" + note
    )
    embed.set_thumbnail(url=get_img_url(int(entry.get('ID', 'N/A'))))  
    await interaction.response.send_message(embed=embed)
    try:
        bot_msg = await interaction.original_response()
        await bot_msg.add_reaction('<:kanade:1481983019463217252>')
    except discord.HTTPException:
        pass

@bot.tree.command(name="song_jacket", description="Get song jacket")
@app_commands.autocomplete(song=song_autocomplete)
async def song_jacket(interaction: discord.Interaction, song: str):
    entry = None
    
    for info in interaction.client.data.values():
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
    try:
        bot_msg = await interaction.original_response()
        await bot_msg.add_reaction('<:kanade:1481983019463217252>')
    except discord.HTTPException:
        pass

@bot.tree.command(name="force_update", description="Force the bot to sync with the spreadsheet")
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
    
@bot.tree.command(name="song_randomizer", description="Randomly choose a list of songs")
async def song_randomizer(interaction: discord.Interaction, 
                          lowest_level:int = None, 
                          highest_level:int = None, 
                          difficulty: Literal["Expert", "Master", "Append"] = None, 
                          amount:int = 5):
    
    song_list = [song for song in interaction.client.data.values() 
                 if (difficulty == None or song['Difficulty'] == difficulty) 
                 and (lowest_level == None or float(song['Ingame Constant']) >= lowest_level)
                 and (highest_level == None or float(song['Ingame Constant']) <= highest_level)]
    
    if not song_list:
        await interaction.response.send_message("No matched songs found!", ephemeral=True)
        return
    
    chosen_list = random.sample(song_list, k=min(amount, len(song_list)))
    
    embed = discord.Embed(
        title="Song Randomizer",
        color=discord.Color.blue(),
        description=f"Found {min(amount, len(song_list))} songs matching your criteria:"
    )
    
    for idx, song in enumerate(chosen_list, 1):
        name = song.get('Song Name', 'Unknown')
        diff = song.get('Difficulty', 'Unknown')
        level = song.get('Ingame Constant', 'N/A')
        embed.add_field(name=f"{idx}. {name}", value=f"**Difficulty:** {diff} | **Level:** {level}", inline=False)

    await interaction.response.send_message(embed=embed)
    try:
        bot_msg = await interaction.original_response()
        await bot_msg.add_reaction('<:kanade:1481983019463217252>')
    except discord.HTTPException:
        pass

class ScoreSelect(discord.ui.Select):
    def __init__(self, song_options, clear_type, info):
        super().__init__(placeholder=f"Select the songs you {clear_type}-ed", 
                         min_values=0, 
                         max_values=len(song_options), 
                         options=song_options)
        self.clear_type = clear_type
        self.info = info

    async def callback(self, interaction: discord.Interaction):
        current_page_keys = {opt.value for opt in self.options}
        
        self.view.selected_keys -= current_page_keys
        
        self.view.selected_keys.update(self.values)

        await self.view.update_message(interaction)

class ScoreView(discord.ui.View):
    def __init__(self, song_list, clear_type, info):
        super().__init__(timeout=600)
        self.song_list = song_list
        self.clear_type = clear_type
        self.info = info
        self.current_page = 0
        self.amount = 25
        self.max_pages = max(1, (len(self.song_list) + self.amount - 1) // self.amount)
        
        self.key_to_name = {song['key']: f"{song['name']} ({song['difficulty']})" for song in self.song_list}

        self.selected_keys = set()

        songs = self.song_list[:self.amount]

        self.select_menu = ScoreSelect([], clear_type, info)
        self.add_item(self.select_menu)
        self.change_page()
        self.update_button_states()

    async def update_message(self, interaction:discord.Interaction):
        if not self.selected_keys:
            text = "Empty"
        else:
            names = [self.key_to_name[key] for key in self.selected_keys]
            text = '\n'.join(names)

            if len(text) > 1500:
                text = text[:1500] + "... (and more)"
                
        content = f"Found {len(self.song_list)} songs! Select your {self.clear_type} clears:\n\n**Current Selection ({len(self.selected_keys)}):**\n`{text}`"
        
        await interaction.response.edit_message(content=content, view=self)
        
    def update_button_states(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.max_pages - 1)

    def change_page(self):
        songs = self.song_list[self.current_page * self.amount: (self.current_page + 1) * self.amount]

        options = [
            discord.SelectOption(
                label=f"{song['name']} ({song['difficulty']})",
                description=f"Constant: {song['const']}",
                value=song['key'],
                default=(song['key'] in self.selected_keys)
            ) for song in songs
        ]

        self.select_menu.options = options
        self.select_menu.max_values = len(options)
        self.update_button_states()

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.change_page()
        await self.update_message(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.change_page()
        await self.update_message(interaction)
    
    @discord.ui.button(label="Confirm & Save", style=discord.ButtonStyle.success, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_keys:
            await interaction.response.send_message("You haven't selected any songs to save!", ephemeral=True)
            return

        await interaction.response.defer()

        records = []
        for key in self.selected_keys:
            const = self.info[key][0]
            difficulty = self.info[key][1]
            song_id = key.split('_')[0] 
            records.append((interaction.user.id, song_id, difficulty, const, self.clear_type))

        await interaction.client.upsert_scores(records)

        for item in self.children:
            item.disabled = True
            
        await interaction.edit_original_response(view=self)

        await interaction.followup.send(f"Successfully saved {len(records)} `{self.clear_type}` score(s)!")

@bot.tree.command(name="log_scores", description="Save new song clears to the database (39s constant) (timeout: 10 mins)")
async def log_score(interaction: discord.Interaction, 
                    clear_type: Literal["FC", "AP"],
                    lowest_level:int = None, 
                    highest_level:int = None, 
                    difficulty: Literal["Expert", "Master", "Append"] = None):
    
    song_list = []
    info = {}
    
    for song in interaction.client.data.values():
        if difficulty is not None and song.get('Difficulty') != difficulty:
            continue

        level = float(song['Ingame Constant'])

        if lowest_level is not None and level < lowest_level:
            continue

        if highest_level is not None and level > highest_level:
            continue

        c_39 = song.get('39s const')
        c_game = song.get('Ingame Constant')
        
        if clear_type == 'AP':
            obg_const = song.get('AP Constant')
        else:
            obg_const = song.get('FC Constant')

        const = get_b30_const(c_39, obg_const, c_game)

        key = f"{song['ID']}_{song['Difficulty']}"

        song_list.append({
            'key': key,
            'name': song['Song Name'],
            'difficulty': song['Difficulty'],
            'const': const
        })

        info[key] =  (const, song['Difficulty'])
    
    if not song_list:
        await interaction.response.send_message("No matched songs found!", ephemeral=True)
        return
    
    song_list.sort(key=lambda x: (-x['const'], x['name']))

    view = ScoreView(song_list, clear_type, info)

    initial_message = f"Found {len(song_list)} songs! Select your {clear_type} clears:\n\n**Current Selection (0):**\n`Empty`"
    await interaction.response.send_message(initial_message, view=view)

    try:
        bot_msg = await interaction.original_response()
        await bot_msg.add_reaction('<:kanade:1481983019463217252>')
    except discord.HTTPException:
        pass

@bot.tree.command(name="log_single_score", description="Log a single song score")
@app_commands.autocomplete(song=song_autocomplete, difficulty=diff_autocomplete)
async def log_single(interaction: discord.Interaction, song: str, difficulty: str, clear_type: Literal["FC", "AP"]):
    entry = None
    for info in interaction.client.data.values():
        if info.get('Song Name', '').lower() == song.lower() and info.get('Difficulty', '').lower() == difficulty.lower():
            entry = info
            break
            
    if not entry:
        await interaction.response.send_message("Song not found", ephemeral=True)
        return

    await interaction.response.defer()
    
    c_39 = entry.get('39s const')
    c_game = entry.get('Ingame Constant', 0.0)
    
    if clear_type == 'AP':
        obg_const = entry.get('AP Constant')
    else:
        obg_const = entry.get('FC Constant')
        
    const = get_b30_const(c_39, obg_const, c_game)

    song_id = entry.get('ID')

    await interaction.client.update_score([(
        interaction.user.id, 
        song_id, 
        difficulty, 
        const, 
        clear_type
    )])

    await interaction.followup.send(f"Successfully logged **{song} ({difficulty})** as a `{clear_type}`!")

@bot.tree.command(name="delete_score", description="Delete a logged score from your profile")
@app_commands.autocomplete(song=song_autocomplete, difficulty=diff_autocomplete)
async def delete_score(interaction: discord.Interaction, song: str, difficulty: str):
    song_id = None
    for info in interaction.client.data.values():
        if info.get('Song Name', '').lower() == song.lower() and info.get('Difficulty', '').lower() == difficulty.lower():
            song_id = info.get('ID')
            break
            
    if not song_id:
        await interaction.response.send_message("Could not find that song in the database", ephemeral=True)
        return
        
    await interaction.response.defer()

    deleted_rows = await interaction.client.remove_score(interaction.user.id, song_id, difficulty)
    
    if deleted_rows > 0:
        await interaction.followup.send(f"Successfully deleted your saved score for **{song} ({difficulty})**!")
        
        try:
            bot_msg = await interaction.original_response()
            await bot_msg.add_reaction('<:kanade:1481983019463217252>')
        except discord.HTTPException:
            pass
            
    else:
        await interaction.followup.send(f"You have no saved score to delete.", ephemeral=True)

bg_literal = Literal[
    "canary",
    "dream",
    "faith",
    "hug",
    "kitty",
    "nsnf",
    "profile1",
    "regret",
    "retie",
    "secret",
    "wanderer"
]

@bot.tree.command(name="b30_ap", description="Generate B30 All Perfect ")
@app_commands.describe(background="Change the background of the generated image (I stole them from the b30 website)")
async def b30_ap(interaction: discord.Interaction, background: bg_literal = "kitty"):
    bg_link = f"assets/background/{background}.png"
    await interaction.response.defer()

    async with interaction.client.db.execute('''
        SELECT song_id, difficulty, constant, clear_type 
        FROM user_scores 
        WHERE user_id = ? AND clear_type = 'AP'
        ORDER BY constant DESC 
        LIMIT 30
    ''', (interaction.user.id,)) as cursor:
        scores = await cursor.fetchall()

    if not scores:
        await interaction.followup.send("You don't have any AP scores logged yet!")
        return

    top_30_songs = []
    total_constant = 0.0

    for song_id, difficulty, constant, clear_type in scores:
        info = interaction.client.data.get((song_id, difficulty))
        song_name = info.get('Song Name') if info else 'Unknown'
        
        total_constant += constant
        top_30_songs.append({
            'id': song_id,
            'name': song_name,
            'difficulty': difficulty,
            'constant': constant,
            'clear_type': clear_type
        })
        
    top_30_songs.sort(key=lambda x: (-x['constant'], x['name']))
    output_filename = f"b30_{interaction.user.id}_ap.png"
    await asyncio.to_thread(generate_b30_image, total_constant / len(top_30_songs), top_30_songs, clear_type, output_filename, bg_link)

    file = discord.File(output_filename)
    await interaction.followup.send(f"{interaction.user.mention}", file=file)
    os.remove(output_filename)

@bot.tree.command(name="b30", description="Generate B30")
@app_commands.describe(background="Change the background of the generated image (I stole them from the b30 website)")
async def b30(interaction: discord.Interaction, background: bg_literal = "kitty"):
    bg_link = f"assets/background/{background}.png"
    await interaction.response.defer()

    async with interaction.client.db.execute('''
        SELECT song_id, difficulty, constant, clear_type 
        FROM user_scores 
        WHERE user_id = ?
    ''', (interaction.user.id,)) as cursor:
        scores = await cursor.fetchall()

    if not scores:
        await interaction.followup.send("You don't have any scores logged yet!")
        return
    
    all_songs = []

    for song_id, difficulty, constant, clear_type in scores:
        info = interaction.client.data.get((song_id, difficulty))
        song_name = info.get('Song Name') if info else 'Unknown'
        
        final_constant = constant if clear_type == 'AP' else constant - 1.0
        
        all_songs.append({
            'id': song_id,
            'name': song_name,
            'difficulty': difficulty,
            'constant': final_constant,
            'clear_type': clear_type
        })
    
    all_songs.sort(key=lambda x: (-x['constant'], x['name']))
    top_30_songs = all_songs[:30]
    
    total_constant = sum(song['constant'] for song in top_30_songs)
    
    output_filename = f"b30_{interaction.user.id}.png"
    await asyncio.to_thread(generate_b30_image, total_constant / len(top_30_songs), top_30_songs, None, output_filename, bg_link)

    file = discord.File(output_filename)
    await interaction.followup.send(f"{interaction.user.mention}", file=file)
    os.remove(output_filename)

bot.run(TOKEN)