import discord
from discord import app_commands

async def song_autocomplete(interaction: discord.Interaction, current: str):
    name_lookup = getattr(interaction.client, 'name_lookup', {})
    q = "".join(current.lower().split())

    seen = set()
    choices = []

    for norm, canonical in name_lookup.items():
        if q not in norm or canonical in seen:
            continue
        seen.add(canonical)
        choices.append(app_commands.Choice(name=canonical, value=canonical))
        if len(choices) >= 10:
            break

    return choices

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