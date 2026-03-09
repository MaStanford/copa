"""Scanner for ~/bin/ script metadata."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .db import Database

# --- Pass 1: #@ Protocol headers (highest priority) ---
PROTOCOL_DESC = re.compile(r"^#@\s*[Dd]escription:\s*(.+)$")
PROTOCOL_USAGE = re.compile(r"^#@\s*[Uu]sage:\s*(.+)$")

# --- Pass 2: Legacy fallback patterns ---
LEGACY_PATTERNS = [
    re.compile(r"^#\s*[Dd]escription:\s*(.+)$"),
    re.compile(r"^#\s*[Pp]urpose:\s*(.+)$"),
    re.compile(r"^#\s*[Uu]sage:\s*(.+)$"),
    re.compile(r'^"""\s*(.+?)(?:""")?$'),  # Python docstring one-liner
    re.compile(r"^#\s*(?![@!])(.{10,80})$"),  # Generic comment (skip @ prefix lines)
]


def extract_description(path: Path) -> str:
    """Extract a description from a script file's header comments.

    Uses a two-pass approach:
      Pass 1 — #@ protocol headers (highest priority)
      Pass 2 — Legacy comment patterns (fallback)
    """
    try:
        with open(path, "r", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= 30:  # Check first 30 lines for protocol headers
                    break
                lines.append(line.rstrip())
    except OSError:
        return ""

    # --- Pass 1: Protocol headers ---
    description = ""
    usage = ""

    for line in lines:
        m = PROTOCOL_DESC.match(line)
        if m:
            description = m.group(1).strip()
            continue
        m = PROTOCOL_USAGE.match(line)
        if m:
            usage = m.group(1).strip()
            continue

    if description:
        if usage:
            return f"{description} | Usage: {usage}"
        return description

    # --- Pass 2: Legacy fallbacks ---
    for line in lines:
        for pattern in LEGACY_PATTERNS:
            m = pattern.match(line)
            if m:
                desc = m.group(1).strip()
                if desc and not desc.startswith("!") and len(desc) > 5:
                    return desc

    return ""


def scan_directory(db: Database, directory: Path | None = None) -> int:
    """Scan a directory for executable scripts and add them to Copa.

    Returns number of scripts added.
    """
    if directory is None:
        directory = Path.home() / "bin"

    if not directory.is_dir():
        return 0

    added = 0
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and os.access(entry, os.X_OK):
            name = entry.name
            # Skip hidden files and common non-script files
            if name.startswith(".") or name.endswith((".md", ".txt", ".log")):
                continue

            description = extract_description(entry)
            if not db.command_exists(name):
                db.add_command(
                    command=name,
                    description=description,
                    source="scan",
                    group_name="bin",
                )
                added += 1

    return added
