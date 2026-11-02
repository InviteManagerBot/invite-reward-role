"""Reward storage in SQLite.

SQLite ships with Python, so there is no database server to install. The
queries touch a handful of rows and take microseconds, so calling them from
async code without a thread pool is fine at this scale.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS rewards (
    guild_id INTEGER NOT NULL,
    role_id  INTEGER NOT NULL,
    invites  INTEGER NOT NULL CHECK (invites > 0),
    PRIMARY KEY (guild_id, role_id)
);
"""


class RewardStore:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def set_reward(self, guild_id: int, role_id: int, invites: int) -> None:
        """Add a reward, or change the invite count of an existing one."""
        with self._db:
            self._db.execute(
                "INSERT INTO rewards (guild_id, role_id, invites) VALUES (?, ?, ?) "
                "ON CONFLICT (guild_id, role_id) DO UPDATE SET invites = excluded.invites",
                (guild_id, role_id, invites),
            )

    def remove_reward(self, guild_id: int, role_id: int) -> bool:
        with self._db:
            cursor = self._db.execute("DELETE FROM rewards WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        return cursor.rowcount > 0

    def list_rewards(self, guild_id: int) -> list[tuple[int, int]]:
        """``(role_id, invites)`` pairs, lowest requirement first."""
        rows = self._db.execute(
            "SELECT role_id, invites FROM rewards WHERE guild_id = ? ORDER BY invites, role_id",
            (guild_id,),
        )
        return list(rows)

    def roles_earned(self, guild_id: int, invites: int) -> list[int]:
        """Every reward role whose requirement is at most ``invites``.

        Using ``<=`` instead of ``=`` also catches up rewards whose alert was
        missed (bot offline, alert added later).
        """
        rows = self._db.execute("SELECT role_id FROM rewards WHERE guild_id = ? AND invites <= ?", (guild_id, invites))
        return [role_id for (role_id,) in rows]
