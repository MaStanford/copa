"""SQLite database layer for Copa."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from .models import Command, SharedSet

DEFAULT_DB_PATH = Path.home() / ".copa" / "copa.db"

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS commands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    command     TEXT NOT NULL,
    description TEXT DEFAULT '',
    frequency   INTEGER DEFAULT 0,
    last_used   REAL DEFAULT 0,
    first_added REAL DEFAULT 0,
    source      TEXT DEFAULT 'manual',
    group_name  TEXT DEFAULT NULL,
    shared_set  TEXT DEFAULT NULL,
    is_pinned   INTEGER DEFAULT 0,
    needs_description INTEGER DEFAULT 0,
    UNIQUE(command, group_name)
);

CREATE TABLE IF NOT EXISTS tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id INTEGER REFERENCES commands(id) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    UNIQUE(command_id, tag)
);

CREATE TABLE IF NOT EXISTS shared_sets (
    name        TEXT PRIMARY KEY,
    description TEXT DEFAULT '',
    source_path TEXT DEFAULT NULL,
    loaded_at   REAL DEFAULT 0,
    version     TEXT DEFAULT '1.0',
    author      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

FTS_SQL = """\
CREATE VIRTUAL TABLE IF NOT EXISTS commands_fts USING fts5(
    command, description, flags, content='commands', content_rowid='id'
);
"""

FTS_TRIGGERS = """\
CREATE TRIGGER IF NOT EXISTS commands_ai AFTER INSERT ON commands BEGIN
    INSERT INTO commands_fts(rowid, command, description, flags)
    VALUES (new.id, new.command, new.description, new.flags);
END;

CREATE TRIGGER IF NOT EXISTS commands_ad AFTER DELETE ON commands BEGIN
    INSERT INTO commands_fts(commands_fts, rowid, command, description, flags)
    VALUES ('delete', old.id, old.command, old.description, old.flags);
END;

CREATE TRIGGER IF NOT EXISTS commands_au AFTER UPDATE ON commands BEGIN
    INSERT INTO commands_fts(commands_fts, rowid, command, description, flags)
    VALUES ('delete', old.id, old.command, old.description, old.flags);
    INSERT INTO commands_fts(rowid, command, description, flags)
    VALUES (new.id, new.command, new.description, new.flags);
END;
"""


class Database:
    """SQLite database for Copa."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_db(self):
        """Create all tables and FTS indexes."""
        cur = self.conn.cursor()
        cur.executescript(SCHEMA_SQL)

        # Migration: add flags column if it doesn't exist yet
        try:
            self.conn.execute("ALTER TABLE commands ADD COLUMN flags TEXT DEFAULT ''")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

        # Rebuild FTS to pick up schema changes (drop old table/triggers first)
        cur.executescript("""
            DROP TRIGGER IF EXISTS commands_ai;
            DROP TRIGGER IF EXISTS commands_ad;
            DROP TRIGGER IF EXISTS commands_au;
            DROP TABLE IF EXISTS commands_fts;
        """)
        cur.executescript(FTS_SQL)
        cur.executescript(FTS_TRIGGERS)

        # Rebuild FTS content from existing data
        cur.execute("""
            INSERT INTO commands_fts(rowid, command, description, flags)
            SELECT id, command, description, COALESCE(flags, '') FROM commands
        """)
        self.conn.commit()

    # --- Commands CRUD ---

    def add_command(
        self,
        command: str,
        description: str = "",
        source: str = "manual",
        group_name: str | None = None,
        shared_set: str | None = None,
        tags: list[str] | None = None,
        needs_description: bool = False,
        flags: dict[str, str] | None = None,
    ) -> int:
        """Add or update a command. Returns the command id."""
        now = time.time()
        flags_json = json.dumps(flags) if flags else ""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """INSERT INTO commands
                   (command, description, frequency, last_used, first_added,
                    source, group_name, shared_set, needs_description, flags)
                   VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)""",
                (command, description, now, now, source, group_name,
                 shared_set, int(needs_description), flags_json),
            )
            cmd_id = cur.lastrowid
        except sqlite3.IntegrityError:
            # Already exists for this group — update
            cur.execute(
                """UPDATE commands
                   SET frequency = frequency + 1, last_used = ?
                   WHERE command = ? AND group_name IS ?""",
                (now, command, group_name),
            )
            cur.execute(
                "SELECT id FROM commands WHERE command = ? AND group_name IS ?",
                (command, group_name),
            )
            cmd_id = cur.fetchone()["id"]
            # Update description if provided and current is empty
            if description:
                cur.execute(
                    """UPDATE commands SET description = ?, needs_description = 0
                       WHERE id = ? AND (description = '' OR description IS NULL)""",
                    (description, cmd_id),
                )

        if tags:
            for tag in tags:
                try:
                    cur.execute(
                        "INSERT INTO tags (command_id, tag) VALUES (?, ?)",
                        (cmd_id, tag),
                    )
                except sqlite3.IntegrityError:
                    pass

        self.conn.commit()
        return cmd_id

    def record_usage(self, command: str):
        """Record a command usage — increment frequency, update last_used."""
        now = time.time()
        cur = self.conn.cursor()
        cur.execute(
            """UPDATE commands SET frequency = frequency + 1, last_used = ?
               WHERE command = ?""",
            (now, command),
        )
        if cur.rowcount == 0:
            # Not tracked yet — add from history
            cur.execute(
                """INSERT INTO commands
                   (command, frequency, last_used, first_added, source)
                   VALUES (?, 1, ?, ?, 'history')""",
                (command, now, now),
            )
        self.conn.commit()

    def get_command(self, cmd_id: int) -> Command | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM commands WHERE id = ?", (cmd_id,))
        row = cur.fetchone()
        if not row:
            return None
        cmd = Command.from_row(dict(row))
        cmd.tags = self._get_tags(cmd_id)
        return cmd

    def remove_command(self, cmd_id: int) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM commands WHERE id = ?", (cmd_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def update_description(self, cmd_id: int, description: str):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE commands SET description = ?, needs_description = 0 WHERE id = ?",
            (description, cmd_id),
        )
        self.conn.commit()

    def update_flags(self, cmd_id: int, flags: dict[str, str]):
        """Update the flags JSON for a command."""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE commands SET flags = ? WHERE id = ?",
            (json.dumps(flags), cmd_id),
        )
        self.conn.commit()

    def pin_command(self, cmd_id: int, pinned: bool = True):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE commands SET is_pinned = ? WHERE id = ?",
            (int(pinned), cmd_id),
        )
        self.conn.commit()

    def update_group(self, cmd_id: int, group_name: str | None) -> bool:
        """Update the group_name for a command.

        Returns False if the same command text already exists in the target
        group (would violate UNIQUE(command, group_name)), True on success.
        """
        cur = self.conn.cursor()
        # Get the command text for this id
        cur.execute("SELECT command FROM commands WHERE id = ?", (cmd_id,))
        row = cur.fetchone()
        if not row:
            return False
        cmd_text = row["command"]

        # Check for UNIQUE conflict: another row with same command text in target group
        cur.execute(
            "SELECT id FROM commands WHERE command = ? AND group_name IS ? AND id != ?",
            (cmd_text, group_name, cmd_id),
        )
        if cur.fetchone():
            return False

        cur.execute(
            "UPDATE commands SET group_name = ? WHERE id = ?",
            (group_name, cmd_id),
        )
        self.conn.commit()
        return True

    # --- Queries ---

    def list_commands(
        self,
        group_name: str | None = None,
        limit: int = 50,
        source: str | None = None,
        needs_description: bool | None = None,
        shared_set: str | None = None,
    ) -> list[Command]:
        """List commands, optionally filtered."""
        clauses = []
        params: list = []

        if group_name is not None:
            clauses.append("group_name = ?")
            params.append(group_name)
        if source is not None:
            clauses.append("source = ?")
            params.append(source)
        if needs_description is not None:
            clauses.append("needs_description = ?")
            params.append(int(needs_description))
        if shared_set is not None:
            clauses.append("shared_set = ?")
            params.append(shared_set)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM commands {where} LIMIT ?", params + [limit])
        rows = cur.fetchall()
        commands = []
        for row in rows:
            cmd = Command.from_row(dict(row))
            cmd.tags = self._get_tags(cmd.id)
            commands.append(cmd)
        return commands

    def search_commands(
        self, query: str, group_name: str | None = None,
        source: str | None = None, shared_set: str | None = None,
        limit: int = 50,
    ) -> list[Command]:
        """FTS5 search across command text and descriptions."""
        cur = self.conn.cursor()
        # Escape FTS special chars and add prefix matching
        safe_query = query.replace('"', '""')
        fts_query = f'"{safe_query}"*'

        clauses = ["commands_fts MATCH ?"]
        params: list = [fts_query]

        if group_name is not None:
            clauses.append("c.group_name = ?")
            params.append(group_name)
        if source is not None:
            clauses.append("c.source = ?")
            params.append(source)
        if shared_set is not None:
            clauses.append("c.shared_set = ?")
            params.append(shared_set)

        where = "WHERE " + " AND ".join(clauses)
        params.append(limit)

        cur.execute(
            f"""SELECT c.* FROM commands c
               JOIN commands_fts f ON c.id = f.rowid
               {where}
               LIMIT ?""",
            params,
        )

        rows = cur.fetchall()
        commands = []
        for row in rows:
            cmd = Command.from_row(dict(row))
            cmd.tags = self._get_tags(cmd.id)
            commands.append(cmd)
        return commands

    def get_all_commands(self) -> list[Command]:
        """Get all commands (for scoring/ranking)."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM commands")
        rows = cur.fetchall()
        commands = []
        for row in rows:
            cmd = Command.from_row(dict(row))
            cmd.tags = self._get_tags(cmd.id)
            commands.append(cmd)
        return commands

    def get_groups(self) -> list[str]:
        """Get all unique group names."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT DISTINCT group_name FROM commands WHERE group_name IS NOT NULL ORDER BY group_name"
        )
        return [row["group_name"] for row in cur.fetchall()]

    def get_sources(self) -> list[str]:
        """Get all unique source values."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT DISTINCT source FROM commands WHERE source IS NOT NULL ORDER BY source"
        )
        return [row["source"] for row in cur.fetchall()]

    def get_stats(self) -> dict:
        """Get usage statistics."""
        cur = self.conn.cursor()
        stats = {}
        cur.execute("SELECT COUNT(*) as total FROM commands")
        stats["total_commands"] = cur.fetchone()["total"]
        cur.execute("SELECT SUM(frequency) as total FROM commands")
        row = cur.fetchone()
        stats["total_uses"] = row["total"] or 0
        cur.execute(
            "SELECT COUNT(DISTINCT group_name) as total FROM commands WHERE group_name IS NOT NULL"
        )
        stats["total_groups"] = cur.fetchone()["total"]
        cur.execute(
            "SELECT COUNT(DISTINCT shared_set) as total FROM commands WHERE shared_set IS NOT NULL"
        )
        stats["shared_sets"] = cur.fetchone()["total"]
        cur.execute(
            "SELECT source, COUNT(*) as cnt FROM commands GROUP BY source ORDER BY cnt DESC"
        )
        stats["by_source"] = {row["source"]: row["cnt"] for row in cur.fetchall()}
        cur.execute(
            "SELECT COUNT(*) as total FROM commands WHERE needs_description = 1"
        )
        stats["needs_description"] = cur.fetchone()["total"]
        cur.execute(
            "SELECT COUNT(*) as total FROM commands WHERE is_pinned = 1"
        )
        stats["pinned"] = cur.fetchone()["total"]
        return stats

    def command_exists(self, command: str, group_name: str | None = None) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM commands WHERE command = ? AND group_name IS ?",
            (command, group_name),
        )
        return cur.fetchone() is not None

    # --- Shared Sets ---

    def upsert_shared_set(self, ss: SharedSet):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO shared_sets (name, description, source_path, loaded_at, version, author)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   description = excluded.description,
                   source_path = excluded.source_path,
                   loaded_at = excluded.loaded_at,
                   version = excluded.version,
                   author = excluded.author""",
            (ss.name, ss.description, ss.source_path, ss.loaded_at, ss.version, ss.author),
        )
        self.conn.commit()

    def get_shared_sets(self) -> list[SharedSet]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM shared_sets ORDER BY name")
        return [SharedSet.from_row(dict(row)) for row in cur.fetchall()]

    def remove_shared_set(self, name: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM commands WHERE shared_set = ?", (name,))
        cur.execute("DELETE FROM shared_sets WHERE name = ?", (name,))
        self.conn.commit()

    # --- Tags ---

    def _get_tags(self, cmd_id: int) -> list[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT tag FROM tags WHERE command_id = ? ORDER BY tag", (cmd_id,))
        return [row["tag"] for row in cur.fetchall()]

    # --- Meta ---

    def get_meta(self, key: str) -> str | None:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()
