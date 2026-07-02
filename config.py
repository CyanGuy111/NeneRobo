import os
from dotenv import load_dotenv
import discord

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
BOT_SERVER_ID = int(os.getenv('BOT_SERVER_ID', 0))

DB_PATH = 'scores.db'

OBG_SHEET_KEY = "1dYo1zlBXFbulieiuVBDmqetOqrw_HRslw0qM-md5Ioo"
SEKAI39S_SHEET_KEY = "1B8tX9VL2PcSJKyuHFVd2UT_8kYlY4ZdwHwg9MfWOPug"

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

KANADE_EMOJI = '<:kanade:1481983019463217252>'

USER_AGENT = os.getenv(
    'USER_AGENT',
    'generic-agent/1.0 (personal project; contact: not-set@example.com)'
)

def get_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    return intents

def get_admin_ids() -> list[int]:
    return [int(i) for i in os.getenv("ADMIN_IDs", "").split(',') if i.strip()]

def get_owner_id() -> int:
    return int(os.getenv("OWNER_ID", 0))