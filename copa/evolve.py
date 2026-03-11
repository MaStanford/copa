"""Auto-evolution: promote frequent history commands to Copa."""

from __future__ import annotations

from .db import Database
from .history import get_history_frequencies

# Trivial commands to skip during auto-evolution
TRIVIAL_COMMANDS = frozenset(
    {
        "ls",
        "ll",
        "la",
        "cd",
        "pwd",
        "clear",
        "exit",
        "quit",
        "fg",
        "bg",
        "jobs",
        "history",
        "which",
        "whoami",
        "date",
        "true",
        "false",
        "yes",
        "no",
        "echo",
        "cat",
        "less",
        "more",
        "head",
        "tail",
        "wc",
        "sort",
        "uniq",
        "grep",
        "find",
        "cp",
        "mv",
        "rm",
        "mkdir",
        "rmdir",
        "touch",
        "chmod",
        "chown",
        "man",
        "help",
        "type",
        "alias",
        "unalias",
        "export",
        "source",
        ".",
        "exec",
    }
)


def is_trivial(cmd: str) -> bool:
    """Check if a command is trivially simple."""
    base = cmd.strip().split()[0] if cmd.strip() else ""
    # Strip path prefix
    base = base.rsplit("/", 1)[-1]
    return base in TRIVIAL_COMMANDS


def evolve(db: Database, top_k: int = 20) -> list[str]:
    """Find top-K frequent history commands not in Copa, add them.

    Returns list of commands added.
    """
    freq = get_history_frequencies()
    if not freq:
        return []

    # Get existing commands
    existing = {cmd.command for cmd in db.get_all_commands()}

    # Filter and rank
    candidates: list[tuple[str, int]] = []
    for cmd, count in freq.most_common():
        if cmd in existing:
            continue
        if is_trivial(cmd):
            continue
        if len(cmd) < 3:
            continue
        candidates.append((cmd, count))
        if len(candidates) >= top_k:
            break

    added = []
    for cmd, count in candidates:
        db.add_command(
            command=cmd,
            source="auto",
            needs_description=True,
        )
        # Set the actual frequency from history
        cur = db.conn.cursor()
        cur.execute(
            "UPDATE commands SET frequency = ? WHERE command = ? AND group_name IS NULL",
            (count, cmd),
        )
        db.conn.commit()
        added.append(cmd)

    return added
