import requests
from config import get_admin_ids, get_owner_id
import discord
from discord import app_commands

def get_b30_const(c_39, obg_const, ingame_const, difficulty=None):
    if c_39 and str(c_39).strip() not in ['N/A', '', '0.0', '0']:
        if difficulty != "Expert" or float(c_39) > 27.0:
            return float(c_39)

    try:
        obg_val = float(obg_const) if obg_const and str(obg_const).strip() not in ['N/A', ''] else 0.0
        game_val = float(ingame_const) if ingame_const and str(ingame_const).strip() not in ['N/A', ''] else 0.0
    except ValueError:
        return 0.0

    if obg_val == 0.0:
        return game_val

    if difficulty == 'Append':
        return obg_val

    if int(obg_val) < int(game_val):
        return float(f"{int(game_val)}.0")
    elif int(obg_val) > int(game_val):
        return float(f"{int(game_val)}.9")
    else:
        return obg_val

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

def get_chart_url(song_id, diff):
    jp_url = f"https://storage.sekai.best/sekai-music-charts/jp/{song_id:04}/{diff.lower()}.png"
    en_url = f"https://storage.sekai.best/sekai-music-charts/en/{song_id:04}/{diff.lower()}.png"

    try:
        response = requests.head(jp_url, timeout=5)
        if response.status_code == 200:
            return jp_url
    except requests.RequestException:
        pass

    return en_url

def is_admin():
    def check(interaction: discord.Interaction) -> bool:
        return interaction.user.id in get_admin_ids()
    return app_commands.check(check)

def is_owner():
    def check(interaction: discord.Interaction) -> bool:
        return interaction.user.id == get_owner_id()
    return app_commands.check(check)