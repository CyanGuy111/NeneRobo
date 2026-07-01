import aiosqlite

from config import DB_PATH
from utils import get_b30_const

class ScoreDatabase:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_scores (
                user_id INTEGER,
                song_id TEXT,
                difficulty TEXT,
                constant REAL,
                clear_type TEXT,
                UNIQUE(user_id, song_id, difficulty)
            )
        ''')
        await self.conn.commit()

    async def close(self):
        if self.conn is not None:
            await self.conn.close()

    async def update_score(self, records: list[tuple]):
        if not records:
            return

        await self.conn.executemany('''
            INSERT OR REPLACE INTO user_scores (user_id, song_id, difficulty, constant, clear_type)
            VALUES (?, ?, ?, ?, ?)
        ''', records)

        await self.conn.commit()

    async def remove_score(self, user_id: int, song_id: str, difficulty: str) -> int:
        async with self.conn.execute('''
            DELETE FROM user_scores
            WHERE user_id = ? AND song_id = ? AND difficulty = ?
        ''', (user_id, song_id, difficulty)) as cursor:
            deleted_rows = cursor.rowcount

        await self.conn.commit()
        return deleted_rows

    async def get_user_scores(self, user_id: int):
        async with self.conn.execute('''
            SELECT song_id, difficulty, constant, clear_type
            FROM user_scores
            WHERE user_id = ?
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()

    async def get_all_scores(self):
        async with self.conn.execute(
            'SELECT user_id, song_id, difficulty, clear_type FROM user_scores'
        ) as cursor:
            return await cursor.fetchall()

    async def sync_constants(self, sheet_data: dict):
        """Recompute stored `constant` values from fresh sheet data."""
        all_scores = await self.get_all_scores()
        update_batch = []

        for user_id, song_id, difficulty, clear_type in all_scores:
            song_info = sheet_data.get((song_id, difficulty))

            if song_info:
                c_39 = song_info.get('39s const')
                c_game = song_info.get('Ingame Constant')

                c_39 = float(c_39) if c_39 and c_39 not in ['N/A', ''] else None
                c_game = float(c_game) if c_game and c_game not in ['N/A', ''] else 0.0

                if clear_type == 'AP':
                    obg_const = song_info.get('AP Constant')
                else:
                    obg_const = song_info.get('FC Constant')

                const = get_b30_const(c_39, obg_const, c_game, difficulty)
                update_batch.append((const, user_id, song_id, difficulty))

        if update_batch:
            await self.conn.executemany('''
                UPDATE user_scores
                SET constant = ?
                WHERE user_id = ? AND song_id = ? AND difficulty = ?
            ''', update_batch)
            await self.conn.commit()