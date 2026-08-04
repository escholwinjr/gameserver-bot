import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATABASE_PATH = Path(__file__).parent / "data" / "players.db"


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                account_name TEXT,
                level INTEGER,
                last_seen TEXT NOT NULL
            )
            """
        )


def save_player(player: dict) -> None:
    last_seen = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            INSERT INTO players (
                player_id,
                user_id,
                name,
                account_name,
                level,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                user_id = excluded.user_id,
                name = excluded.name,
                account_name = excluded.account_name,
                level = excluded.level,
                last_seen = excluded.last_seen
            """,
            (
                player.get("playerId"),
                player.get("userId"),
                player.get("name", "Unknown"),
                player.get("accountName"),
                player.get("level"),
                last_seen,
            ),
        )


def get_player_by_name(name: str) -> Optional[dict]:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            """
            SELECT
                player_id,
                user_id,
                name,
                account_name,
                level,
                last_seen
            FROM players
            WHERE name = ? COLLATE NOCASE
            """,
            (name,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)
