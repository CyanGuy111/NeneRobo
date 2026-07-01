import random
from typing import Literal

import discord
from discord import app_commands

from config import KANADE_EMOJI
from utils import get_img_url, get_chart_url
from autocomplete import song_autocomplete, diff_autocomplete, chart_diff_autocomplete

song_group = app_commands.Group(name="song", description="Commands for looking up song data")

async def _react_kanade(interaction: discord.Interaction):
    try:
        bot_msg = await interaction.original_response()
        await bot_msg.add_reaction(KANADE_EMOJI)
    except discord.HTTPException:
        pass

@song_group.command(name="constant", description="Get song details")
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
    dFC = entry.get('𝚫FC', 'N/A')
    dAP = entry.get('𝚫AP', 'N/A')
    jp_name = entry.get('Japanese name', 'N/A')
    note = f"**Note:** `{entry.get('Notes')}`" if entry.get('Notes') else ""

    embed = discord.Embed(
        title=entry.get('Song Name', 'Unknown'),
        description=f"**Difficulty:** {entry.get('Difficulty', 'Unknown')}\n"
                    f"**JP name:** `{jp_name if jp_name != '' else 'N/A'}`\n"
                    f"**Level:** `{entry.get('Ingame Constant', 'N/A')}`\n"
                    f"**39s Constant:** `{entry.get('39s const', 'N/A')}`\n"
                    f"**FC Constant (OBS list):** `{FC_const if FC_const != '0.0' else 'N/A'}{f" (±{dFC})" if dFC != "0.0" else ""}`\n"
                    f"**AP Constant (OBS list):** `{AP_const if AP_const != '0.0' else 'N/A'}{f" (±{dAP})" if dAP != "0.0" else ""}`\n" + note
    )
    embed.set_thumbnail(url=get_img_url(int(entry.get('ID', 0))))
    await interaction.response.send_message(embed=embed)
    await _react_kanade(interaction)

@song_group.command(name="jacket")
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
    embed.set_image(url=get_img_url(int(entry.get('ID', 0))))
    await interaction.response.send_message(embed=embed)
    await _react_kanade(interaction)

@song_group.command(name="randomizer", description="Get song details")
async def song_randomizer(interaction: discord.Interaction,
                          lowest_level: int = None,
                          highest_level: int = None,
                          difficulty: Literal["Expert", "Master", "Append"] = None,
                          amount: int = 5):

    song_list = []

    for song in interaction.client.data.values():
        try:
            ingame_const = float(song.get('Ingame Constant', 0.0))
        except (TypeError, ValueError):
            continue

        if ((difficulty is None or song.get('Difficulty') == difficulty)
            and (lowest_level is None or ingame_const >= lowest_level)
            and (highest_level is None or ingame_const <= highest_level)):

            song_list.append(song)

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
    await _react_kanade(interaction)

@song_group.command(name="chart")
@app_commands.autocomplete(song=song_autocomplete, difficulty=chart_diff_autocomplete)
async def song_chart(interaction: discord.Interaction, song: str, difficulty: str = 'Master'):
    entry = None

    for info in interaction.client.data.values():
        if info.get('Song Name', '').lower() == song.lower():
            entry = info
            break

    if not entry:
        await interaction.response.send_message("Song not found!", ephemeral=True)
        return

    song_id = int(entry.get('ID', 0)) 

    embed = discord.Embed(
        title=entry.get('Song Name', 'Unknown'),
        description=f"**Difficulty:** {difficulty}\n"
    )
    chart_url = get_chart_url(song_id, difficulty.lower())
    embed.set_image(url= chart_url)
    view = discord.ui.View()
    button = discord.ui.Button(label="File", style=discord.ButtonStyle.link, url=chart_url)
    view.add_item(button)
    await interaction.response.send_message(embed=embed, view=view)
    await _react_kanade(interaction)