import asyncio

import gspread
from google.oauth2.service_account import Credentials

from config import SERVICE_ACCOUNT_FILE, SHEETS_SCOPES, OBG_SHEET_KEY

_creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SHEETS_SCOPES)
client = gspread.authorize(_creds)

def _fetch_obg_raw():
    return client.open_by_key(OBG_SHEET_KEY).sheet1.get_all_values()

async def fetch_song_data() -> tuple[dict, list, list]:
    """Fetches and merges OBG + 39s sheet data.

    Returns (data, unique_songs) where data maps (song_id, difficulty) -> info dict.
    On failure of a given sheet, prints an error and continues with what it has.
    """
    print("Fetching fresh data from Google Sheets...")

    data = {}
    unique_songs = []
    normalized_names = []

    try:
        raw_data = await asyncio.to_thread(_fetch_obg_raw)

        if raw_data:
            headers = raw_data[1][:9] + ['Notes']
            headers[1] = "Song Name"
            headers[2] = "Japanese name"
            parsed = []

            for row in raw_data[2:]:
                if not row:
                    continue

                padded_row = row + ([""] * (20 - len(row)))
                parsed.append(dict(zip(headers, padded_row[:9] + [padded_row[-1]])))

            data = {(i.get('ID'), i.get('Difficulty')): i for i in parsed if i.get('ID') and i.get('Difficulty')}
            unique_songs = sorted(list(set(info.get('Song Name', '') for info in data.values() if info.get('Song Name'))))
            normalized_names = [(("".join(name.lower().split())), name) for name in unique_songs]

            print("Successfully cached OBG")

    except Exception as e:
        print(f"Failed to update data (OBG): {e}")

    return data, unique_songs, normalized_names