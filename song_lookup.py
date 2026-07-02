def find_song_entry(client, song: str, difficulty: str = None):
    name_lookup = getattr(client, 'name_lookup', {})
    target = "".join(song.lower().split())
    resolved = name_lookup.get(target, song)

    for info in client.data.values():
        if info.get('Song Name', '').lower() != resolved.lower():
            continue
        if difficulty is not None and info.get('Difficulty', '').lower() != difficulty.lower():
            continue
        return info

    return None