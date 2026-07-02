def load_aliases(path: str = None) -> dict[str, str]:
    return {}

def resolve_song_name(song: str, alias_map: dict[str, str]) -> str:
    return song