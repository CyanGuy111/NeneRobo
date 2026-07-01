import os
import asyncio
from typing import Literal

import discord
from discord import app_commands

from config import KANADE_EMOJI
from utils import get_b30_const
from autocomplete import song_autocomplete, diff_autocomplete
from views import ScoreView
from image_gen import generate_b30_image

record_group = app_commands.Group(name="record", description="Commands for adding/deleting personal plays to the bot database")

async def _react_kanade(interaction: discord.Interaction):
    try:
        bot_msg = await interaction.original_response()
        await bot_msg.add_reaction(KANADE_EMOJI)
    except discord.HTTPException:
        pass

@record_group.command(name="add_bulk", description="Save new song clears to the database (39s constant) (timeout: 10 mins)")
async def log_score(interaction: discord.Interaction,
                    clear_type: Literal["FC", "AP"],
                    lowest_level: int = None,
                    highest_level: int = None,
                    difficulty: Literal["Expert", "Master", "Append"] = None):

    song_list = []
    info = {}

    for song in interaction.client.data.values():
        if difficulty is not None and song.get('Difficulty') != difficulty:
            continue

        try:
            level = float(song.get('Ingame Constant', 0.0))
        except (TypeError, ValueError):
            continue

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

        const = get_b30_const(c_39, obg_const, c_game, song.get('Difficulty'))

        key = f"{song.get('ID')}_{song.get('Difficulty')}"

        song_list.append({
            'key': key,
            'name': song.get('Song Name', 'Unknown'),
            'difficulty': song.get('Difficulty', 'Unknown'),
            'const': const
        })

        info[key] = (const, song.get('Difficulty'))

    if not song_list:
        await interaction.response.send_message("No matched songs found!", ephemeral=True)
        return

    song_list.sort(key=lambda x: (-x.get('const', 0.0), x.get('name', '')))

    view = ScoreView(song_list, clear_type, info)

    initial_message = f"Found {len(song_list)} songs! Select your {clear_type} clears:\n\n**Current Selection (0):**\n`Empty`"
    await interaction.response.send_message(initial_message, view=view)

    await _react_kanade(interaction)

@record_group.command(name="add_single", description="Log a single song score")
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

    const = get_b30_const(c_39, obg_const, c_game, difficulty)

    song_id = entry.get('ID')

    if song_id is not None:
        await interaction.client.db.update_score([(
            interaction.user.id,
            song_id,
            difficulty,
            const,
            clear_type
        )])
        await interaction.followup.send(f"Successfully logged **{song} ({difficulty})** as a `{clear_type}`!")
    else:
        await interaction.followup.send("Error logging score, missing song ID.")

    await _react_kanade(interaction)

@record_group.command(name="delete", description="Delete a logged score from your profile")
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

    deleted_rows = await interaction.client.db.remove_score(interaction.user.id, song_id, difficulty)

    if deleted_rows > 0:
        await interaction.followup.send(f"Successfully deleted your saved score for **{song} ({difficulty})**!")
    else:
        await interaction.followup.send("You have no saved score to delete.", ephemeral=True)

    await _react_kanade(interaction)

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

def register_b30_command(bot):
    @bot.tree.command(name="b30", description="Generate your Best 30 profile")
    @app_commands.describe(
        background="Change the background of the generated image (I stole them from the b30 website)",
        is_ap_only="Set to True to generate a B30 using only AP scores"
    )
    async def b30(interaction: discord.Interaction, background: bg_literal = "kitty", is_ap_only: bool = False, is_japanese: bool = False):
        bg_link = f"assets/background/{background}.png"
        await interaction.response.defer()

        scores = await interaction.client.db.get_user_scores(interaction.user.id)

        if not scores:
            await interaction.followup.send("You don't have any scores logged yet!")
            return

        all_songs = []

        for song_id, difficulty, constant, clear_type in scores:
            if is_ap_only and clear_type != 'AP':
                continue

            info = interaction.client.data.get((song_id, difficulty))

            if is_japanese:
                song_name = info.get('Japanese name') if info else 'Unknown'
            else:
                song_name = info.get('Song Name') if info else 'Unknown'

            final_constant = constant if clear_type == 'AP' else constant - 1.0

            all_songs.append({
                'id': song_id,
                'name': song_name,
                'difficulty': difficulty,
                'constant': final_constant,
                'clear_type': clear_type
            })

        if not all_songs:
            await interaction.followup.send("You don't have any AP scores logged yet!")
            return

        all_songs.sort(key=lambda x: (-x.get('constant', 0.0), x.get('name', '')))
        top_30_songs = all_songs[:30]

        total_constant = sum(song.get('constant', 0.0) for song in top_30_songs)

        file_suffix = "_ap" if is_ap_only else ""
        output_filename = f"b30_{interaction.user.id}{file_suffix}.png"

        image_mode = 'AP' if is_ap_only else None

        await asyncio.to_thread(
            generate_b30_image,
            total_constant / len(top_30_songs) if len(top_30_songs) > 0 else 0,
            top_30_songs,
            image_mode,
            output_filename,
            bg_link
        )

        file = discord.File(output_filename)
        await interaction.followup.send(f"{interaction.user.mention}", file=file)
        try:
            bot_msg = await interaction.original_response()
            await bot_msg.add_reaction(KANADE_EMOJI)
        except discord.HTTPException:
            pass
        os.remove(output_filename)