"""fzf integration for Copa."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime

from .db import Database
from .models import Command
from .scoring import rank_commands


def has_fzf() -> bool:
    """Check if fzf is installed."""
    return shutil.which("fzf") is not None


def format_line(cmd: Command) -> str:
    """Format a command for fzf display.

    Format: ID ┃ command ┃ description ┃ [group] ┃ freq×N
    """
    parts = [f"{cmd.id:>5}"]
    parts.append(cmd.command)

    desc = cmd.description[:60] if cmd.description else ""
    parts.append(desc)

    meta = []
    if cmd.group_name:
        meta.append(f"[{cmd.group_name}]")
    if cmd.shared_set:
        meta.append(f"[shared:{cmd.shared_set}]")
    if cmd.is_pinned:
        meta.append("[pinned]")
    meta.append(f"{cmd.frequency}×")
    parts.append(" ".join(meta))

    return " ┃ ".join(parts)


def format_preview(cmd: Command) -> str:
    """Format a rich preview for fzf preview pane."""
    lines = []
    lines.append(f"Command:     {cmd.command}")
    lines.append(f"Description: {cmd.description or '(none)'}")
    lines.append(f"Score:       {cmd.score:.1f}")
    lines.append(f"Frequency:   {cmd.frequency}")
    if cmd.last_used > 0:
        dt = datetime.fromtimestamp(cmd.last_used)
        lines.append(f"Last used:   {dt.strftime('%Y-%m-%d %H:%M')}")
    if cmd.first_added > 0:
        dt = datetime.fromtimestamp(cmd.first_added)
        lines.append(f"First added: {dt.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Source:      {cmd.source}")
    if cmd.group_name:
        lines.append(f"Group:       {cmd.group_name}")
    if cmd.shared_set:
        lines.append(f"Shared set:  {cmd.shared_set}")
    if cmd.is_pinned:
        lines.append("Pinned:      yes")
    if cmd.tags:
        lines.append(f"Tags:        {', '.join(cmd.tags)}")
    return "\n".join(lines)


def fzf_list(
    db: Database, mode: str = "all", group: str | None = None,
    shared_set: str | None = None,
) -> list[str]:
    """Generate fzf-compatible output lines.

    Modes: all, frequent, recent, group, set
    """
    if mode == "set" and shared_set:
        commands = db.list_commands(shared_set=shared_set, limit=500)
    elif mode == "group" and group:
        commands = db.list_commands(group_name=group, limit=500)
    elif shared_set:
        commands = db.list_commands(shared_set=shared_set, limit=500)
    else:
        commands = db.get_all_commands()

    ranked = rank_commands(commands)

    if mode == "recent":
        ranked.sort(key=lambda c: c.last_used, reverse=True)
    elif mode == "frequent":
        ranked.sort(key=lambda c: c.frequency, reverse=True)

    return [format_line(cmd) for cmd in ranked]


def run_fzf(db: Database, mode: str = "all", group: str | None = None) -> str | None:
    """Run fzf with Copa commands. Returns selected command text or None."""
    if not has_fzf():
        print("Error: fzf is not installed. Install with: brew install fzf", file=sys.stderr)
        return None

    lines = fzf_list(db, mode=mode, group=group)
    if not lines:
        print("No commands found.", file=sys.stderr)
        return None

    input_text = "\n".join(lines)

    # Find the copa executable for preview
    copa_bin = shutil.which("copa") or sys.argv[0]
    preview_cmd = f"{copa_bin} _preview {{1}}"

    try:
        result = subprocess.run(
            [
                "fzf",
                "--ansi",
                "--delimiter", "┃",
                "--with-nth", "2..",
                "--preview", preview_cmd,
                "--preview-window", "right:40%:wrap",
                "--header", f"Copa [{mode}] — Tab to cycle modes",
                "--prompt", "copa> ",
                "--height", "80%",
                "--layout", "reverse",
                "--bind", "enter:accept",
            ],
            input=input_text,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Error: fzf not found", file=sys.stderr)
        return None

    if result.returncode != 0:
        return None

    selected = result.stdout.strip()
    if not selected:
        return None

    # Extract command text (second field after ┃)
    parts = selected.split("┃")
    if len(parts) >= 2:
        return parts[1].strip()
    return selected.strip()
