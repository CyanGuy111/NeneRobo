from config import TOKEN
from bot import bot
from commands.song import song_group
from commands.record import record_group, register_b30_command
from commands.admin import register_admin_commands

register_admin_commands(bot)
register_b30_command(bot)

bot.tree.add_command(song_group)
bot.tree.add_command(record_group)

if __name__ == '__main__':
    bot.run(TOKEN)