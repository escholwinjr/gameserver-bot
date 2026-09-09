import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from games.palworld import player_store


class PlayerStoreCompatibilityTests(unittest.TestCase):
    def test_database_stays_at_repository_root(self):
        repository = Path(__file__).resolve().parents[2]
        self.assertEqual(
            player_store.DATABASE_PATH.resolve(),
            repository / "data" / "players.db",
        )

    def test_existing_players_and_reaction_role_state_survive_initialization(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as cleanup:
            database = Path(directory) / "players.db"
            connect = sqlite3.connect

            def tracked_connect(*args, **kwargs):
                connection = connect(*args, **kwargs)
                cleanup.callback(connection.close)
                return connection

            cleanup.enter_context(patch.object(sqlite3, "connect", tracked_connect))
            with sqlite3.connect(database) as connection:
                connection.executescript("""
                    CREATE TABLE players (
                        player_id TEXT PRIMARY KEY, user_id TEXT,
                        name TEXT NOT NULL, account_name TEXT,
                        level INTEGER, last_seen TEXT NOT NULL
                    );
                    INSERT INTO players VALUES (
                        'player-1', 'steam-1', 'Existing Player',
                        'Existing Account', 42, '2026-01-01T00:00:00+00:00'
                    );
                    CREATE TABLE bot_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    INSERT INTO bot_state VALUES (
                        'reaction_role_selector_message_id', '123456789'
                    );
                """)

            with patch.object(player_store, "DATABASE_PATH", database):
                player_store.initialize_database()
                player = player_store.get_player_by_name("existing player")
                self.assertEqual(player["player_id"], "player-1")
                self.assertEqual(player["level"], 42)
                self.assertEqual(
                    player_store.get_bot_state("reaction_role_selector_message_id"),
                    "123456789",
                )
                player_store.save_player({
                    "playerId": "player-1", "userId": "steam-1",
                    "name": "Existing Player", "accountName": "Existing Account",
                    "level": 43,
                })
                self.assertEqual(
                    player_store.get_player_by_name("Existing Player")["level"], 43
                )


if __name__ == "__main__":
    unittest.main()
