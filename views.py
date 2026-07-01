import discord

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

        self.key_to_name = {song.get('key'): f"{song.get('name')} ({song.get('difficulty')})" for song in self.song_list if song.get('key')}

        self.selected_keys = set()

        self.select_menu = ScoreSelect([], clear_type, info)
        self.add_item(self.select_menu)
        self.change_page()
        self.update_button_states()

    async def update_message(self, interaction: discord.Interaction):
        if not self.selected_keys:
            text = "Empty"
        else:
            names = [self.key_to_name.get(key, "Unknown") for key in self.selected_keys]
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
                label=f"{song.get('name')} ({song.get('difficulty')})",
                description=f"Constant: {song.get('const')}",
                value=song.get('key'),
                default=(song.get('key') in self.selected_keys)
            ) for song in songs if song.get('key')
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
            if key in self.info:
                const = self.info[key][0]
                difficulty = self.info[key][1]
                song_id = key.split('_')[0]
                records.append((interaction.user.id, song_id, difficulty, const, self.clear_type))

        await interaction.client.db.update_score(records)

        for item in self.children:
            item.disabled = True

        await interaction.edit_original_response(view=self)

        await interaction.followup.send(f"Successfully saved {len(records)} `{self.clear_type}` score(s)!")