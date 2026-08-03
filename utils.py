import requests
from config import get_admin_ids, get_owner_id
import discord
from discord import app_commands
import math

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def get_b30_const(obg_const, ingame_const, difficulty=None):
    try:
        obg_val = float(obg_const) if obg_const and str(obg_const).strip() not in ['N/A', ''] else 0.0
        game_val = float(ingame_const) if ingame_const and str(ingame_const).strip() not in ['N/A', ''] else 0.0
    except ValueError:
        return 0.0

    if obg_val == 0.0:
        return game_val

    if difficulty == 'Append':
        return obg_val

    obg_val = game_val + 0.9 * sigmoid(3.67 * (obg_val - game_val - 0.45)) # i LOVE magic numbers!!!!
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