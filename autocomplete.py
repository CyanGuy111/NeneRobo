import discord
from discord import app_commands

async def song_autocomplete(interaction: discord.Interaction, current: str):
    unique_songs = getattr(interaction.client, '_normalized_names', [])
    q = "".join(current.lower().split())
    return [
        app_commands.Choice(name=orig, value=orig)
        for norm, orig in unique_songs if q in norm
    ][:10]

async def diff_autocomplete(interaction: discord.Interaction, current: str):
    chosen_song = getattr(interaction.namespace, 'song', None)

    available_diffs = [
        info.get('Difficulty', '') for info in interaction.client.data.values()
        if info.get('Song Name', '').lower() == (chosen_song or "").lower()
    ]

    return [
        app_commands.Choice(name=d.title(), value=d)
        for d in available_diffs if current.lower() in d.lower()
    ][:10]

BASE_CHART_DIFFICULTIES = ["Easy", "Normal", "Hard", "Expert", "Master"]
 
async def chart_diff_autocomplete(interaction: discord.Interaction, current: str):
    chosen_song = getattr(interaction.namespace, 'song', None)
 
    options = list(BASE_CHART_DIFFICULTIES)
 
    has_append = any(
        info.get('Song Name', '').lower() == (chosen_song or "").lower()
        and info.get('Difficulty') == 'Append'
        for info in interaction.client.data.values()
    )
    
    if has_append:
        options.append("Append")
 
    return [
        app_commands.Choice(name=d, value=d)
        for d in options if current.lower() in d.lower()
    ][:10]