import asyncio
import json
import time
from pathlib import Path

import requests

from config import USER_AGENT

API_URL = "https://www.sekaipedia.org/w/api.php"
TABLE = "songs"
BATCH_SIZE = 500
REQUEST_DELAY = 0.5
REQUEST_TIMEOUT = 15
CACHE_FILE = "song_metadata.json"

HEADERS = {
    "User-Agent": USER_AGENT,
    # if you see "Failed to refresh romaji data, keeping existing cache: 403 Client Error: Forbidden for url: 
    # https://www.sekaipedia.org/w/api.php?action=cargofields&table=songs&format=json", uncomment the following
    # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    # "Accept-Language": "en-US,en;q=0.9",
    # "Referer": "https://www.sekaipedia.org/",
    # "Origin": "https://www.sekaipedia.org",
    # "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    # "Sec-Ch-Ua-Mobile": "?0",
    # "Sec-Ch-Ua-Platform": '"Windows"',
    # "Sec-Fetch-Dest": "empty",
    # "Sec-Fetch-Mode": "cors",
    # "Sec-Fetch-Site": "same-origin",
}

def _get(params: dict) -> dict:
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def _get_fields(table: str) -> list[str]:
    data = _get({"action": "cargofields", "table": table, "format": "json"})
    if "cargofields" not in data:
        raise RuntimeError(f"Unexpected response from cargofields: {data}")
    return list(data["cargofields"].keys())

def _fetch_all_rows(field_map: dict[str, str]) -> list[dict]:
    fields_param = ",".join(f"{col}={alias}" for col, alias in field_map.items())
    all_rows = []
    offset = 0

    while True:
        data = _get({
            "action": "cargoquery",
            "tables": TABLE,
            "fields": fields_param,
            "limit": BATCH_SIZE,
            "offset": offset,
            "format": "json",
        })

        if "error" in data:
            raise RuntimeError(f"Cargo query error: {data['error']}")

        batch = [item["title"] for item in data.get("cargoquery", [])]
        if not batch:
            break

        all_rows.extend(batch)

        if len(batch) < BATCH_SIZE:
            break

        offset += BATCH_SIZE
        time.sleep(REQUEST_DELAY)

    return all_rows

def _fetch_romaji_sync() -> dict[str, str]:
    """Blocking implementation - run via asyncio.to_thread from async code."""
    fields = _get_fields(TABLE)

    if "romaji" not in fields:
        raise RuntimeError(f"'romaji' field not found on Cargo table. Available fields: {fields}")

    rows = _fetch_all_rows({"song_id": "song_id", "romaji": "romaji"})

    result = {}
    for row in rows:
        song_id = row.get("song_id")
        romaji = row.get("romaji")
        if song_id and romaji:
            result[str(song_id)] = romaji

    return result

def load_romaji_cache(path: str = CACHE_FILE) -> dict[str, str]:
    file = Path(path)
    if not file.exists():
        return {}
    try:
        with open(file, encoding='utf-8') as f:
            raw = json.load(f)
    except Exception:
        return {}

    result = {}
    for song_id, value in raw.items():
        romaji = value.get("romaji") if isinstance(value, dict) else value
        if romaji:
            result[str(song_id)] = romaji
    return result

def save_romaji_cache(romaji_map: dict[str, str], path: str = CACHE_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(romaji_map, f, ensure_ascii=False, indent=2)

async def refresh_romaji(path: str = CACHE_FILE) -> dict[str, str]:
    """Fetches fresh romaji data from Sekaipedia and writes it to the cache file.
    Raises on failure - caller decides whether to keep using the old cached map."""
    romaji_map = await asyncio.to_thread(_fetch_romaji_sync)
    save_romaji_cache(romaji_map, path)
    return romaji_map