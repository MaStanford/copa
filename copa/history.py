"""Zsh history ingestion for Copa."""

from __future__ import annotations

import re
import time
from collections import Counter
from pathlib import Path

from .db import Database

# Default zsh history file
DEFAULT_HISTORY = Path.home() / ".zsh_history"

# Extended history format: : timestamp:0;command
EXTENDED_RE = re.compile(r"^:\s*(\d+):\d+;(.+)$")


def parse_zsh_history(
    history_path: Path | None = None,
) -> list[tuple[str, float]]:
    """Parse zsh history, returning (command, timestamp) tuples.

    Handles both plain and extended history formats.
    Multi-line commands (ending with \\) are joined.
    """
    if history_path is None:
        history_path = DEFAULT_HISTORY

    if not history_path.exists():
        return []

    entries: list[tuple[str, float]] = []

    try:
        raw = history_path.read_bytes()
        # Zsh history may use meta-encoding; decode with replacement
        text = raw.decode("utf-8", errors="replace")
    except OSError:
        return []

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # Extended format
        m = EXTENDED_RE.match(line)
        if m:
            ts = float(m.group(1))
            cmd = m.group(2)
            # Handle continuation lines
            while cmd.endswith("\\") and i + 1 < len(lines):
                i += 1
                cmd = cmd[:-1] + "\n" + lines[i]
            entries.append((cmd.strip(), ts))
        elif line.strip():
            # Plain format — no timestamp
            cmd = line.strip()
            while cmd.endswith("\\") and i + 1 < len(lines):
                i += 1
                cmd = cmd[:-1] + "\n" + lines[i]
            entries.append((cmd.strip(), 0.0))

        i += 1

    return entries


def sync_history(
    db: Database,
    history_path: Path | None = None,
) -> int:
    """Ingest zsh history into Copa database.

    Returns the number of new commands added.
    """
    entries = parse_zsh_history(history_path)
    if not entries:
        return 0

    # Count frequencies
    freq: Counter[str] = Counter()
    latest_ts: dict[str, float] = {}
    for cmd, ts in entries:
        freq[cmd] += 1
        if ts > latest_ts.get(cmd, 0):
            latest_ts[cmd] = ts

    added = 0
    now = time.time()
    cur = db.conn.cursor()

    for cmd, count in freq.items():
        # Skip trivially short or empty commands
        if len(cmd) < 2:
            continue

        ts = latest_ts.get(cmd, now)
        existing = cur.execute(
            "SELECT id, frequency FROM commands WHERE command = ? AND group_name IS NULL",
            (cmd,),
        ).fetchone()

        if existing:
            # Update frequency and last_used if history is newer
            cur.execute(
                """UPDATE commands
                   SET frequency = MAX(frequency, ?),
                       last_used = MAX(last_used, ?)
                   WHERE id = ?""",
                (count, ts, existing["id"]),
            )
        else:
            cur.execute(
                """INSERT INTO commands
                   (command, frequency, last_used, first_added, source)
                   VALUES (?, ?, ?, ?, 'history')""",
                (cmd, count, ts, ts),
            )
            added += 1

    db.conn.commit()
    return added


def get_history_frequencies(
    history_path: Path | None = None,
) -> Counter[str]:
    """Get command frequencies from zsh history."""
    entries = parse_zsh_history(history_path)
    return Counter(cmd for cmd, _ in entries)
