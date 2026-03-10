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


# ANSI escape codes
_DIM = "\033[2m"
_MAGENTA = "\033[35m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


def format_lines(commands: list[Command]) -> list[str]:
    """Format commands for fzf display with aligned columns.

    Layout: {id} ┃ {command (padded)} ┃ {pin}{group_badge}  {freq} ┃ {search_text}
    Field 1 (ID) is hidden by fzf --with-nth '2..3'.
    Field 2 (command) is extracted by cut -d'┃' -f2 in copa.zsh.
    Field 3 (metadata) is visible but not extracted.
    Field 4 (description+flags) is hidden but searchable by fzf.
    """
    if not commands:
        return []

    # Compute column widths from the full list
    max_cmd = min(max(len(c.command) for c in commands), 60)
    max_grp = max(
        (len(f"[{c.group_name}]") for c in commands if c.group_name),
        default=0,
    )

    lines = []
    for cmd in commands:
        # Field 1: hidden ID
        id_field = f"{cmd.id:>5}"

        # Field 2: command text, padded for column alignment
        cmd_text = cmd.command
        if len(cmd_text) > 60:
            cmd_text = cmd_text[:57] + "..."
        cmd_field = f" {cmd_text:<{max_cmd}} "

        # Field 3: metadata — pin indicator, group badge, frequency
        pin = f"{_YELLOW}*{_RESET} " if cmd.is_pinned else "  "

        if cmd.group_name:
            badge = f"[{cmd.group_name}]"
            padded_badge = f"{badge:>{max_grp}}"
            grp = f"{_DIM}{_MAGENTA}{padded_badge}{_RESET}"
        else:
            grp = " " * max_grp

        freq_str = f"{cmd.frequency}×"
        freq = f"{_DIM}{freq_str:>6}{_RESET}"

        meta_field = f" {pin}{grp}  {freq}"

        # Field 4: hidden searchable text (description, usage, purpose, flags)
        search_text = cmd.description or ""
        if cmd.flags:
            search_text += " " + " ".join(f"{k} {v}" for k, v in cmd.flags.items())

        lines.append(f"{id_field} ┃{cmd_field}┃{meta_field}┃ {search_text}")

    return lines


def _parse_description(desc: str) -> dict[str, str]:
    """Parse a structured description string into its components.

    Handles both plain descriptions and structured format:
      "Description text | Usage: X | Purpose: Y"

    Returns dict with keys: description, usage, purpose.
    """
    result = {"description": "", "usage": "", "purpose": ""}
    if not desc:
        return result

    # Split on " | " and check for known prefixes
    parts = [p.strip() for p in desc.split(" | ")]
    for part in parts:
        if part.startswith("Usage: "):
            result["usage"] = part[7:]
        elif part.startswith("Purpose: "):
            result["purpose"] = part[9:]
        elif not result["description"]:
            result["description"] = part

    return result


def format_preview(cmd: Command) -> str:
    """Format a rich preview for fzf preview pane."""
    lines = []
    lines.append(f"Command:     {cmd.command}")

    parsed = _parse_description(cmd.description)
    lines.append(f"Description: {parsed['description'] or '(none)'}")
    if parsed["usage"]:
        lines.append(f"Usage:       {parsed['usage']}")
    if parsed["purpose"]:
        lines.append(f"Purpose:     {parsed['purpose']}")

    if cmd.flags:
        lines.append("")
        lines.append("Flags:")
        for flag, desc in cmd.flags.items():
            lines.append(f"  {flag:20s} {desc}")
        lines.append("")

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

    return format_lines(ranked)


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
                "--with-nth", "2..3",
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
