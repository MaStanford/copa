"""Scanner for executable script metadata across $PATH."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .db import Database

# --- Pass 1: #@ Protocol headers (highest priority) ---
PROTOCOL_DESC = re.compile(r"^#@\s*[Dd]escription:\s*(.+)$")
PROTOCOL_USAGE = re.compile(r"^#@\s*[Uu]sage:\s*(.+)$")
PROTOCOL_PURPOSE = re.compile(r"^#@\s*[Pp]urpose:\s*(.+)$")
PROTOCOL_FLAG = re.compile(r"^#@\s*[Ff]lag:\s*(.+)$")

# --- Pass 2: Legacy fallback patterns ---
LEGACY_PATTERNS = [
    re.compile(r"^#\s*[Dd]escription:\s*(.+)$"),
    re.compile(r"^#\s*[Pp]urpose:\s*(.+)$"),
    re.compile(r"^#\s*[Uu]sage:\s*(.+)$"),
    re.compile(r'^"""\s*(.+?)(?:""")?$'),  # Python docstring one-liner
    re.compile(r"^#\s*(?![@!])(.{10,80})$"),  # Generic comment (skip @ prefix lines)
]


def extract_description(path: Path) -> tuple[str, dict[str, str]]:
    """Extract a description and flags from a script file's header comments.

    Uses a two-pass approach:
      Pass 1 — #@ protocol headers (highest priority)
      Pass 2 — Legacy comment patterns (fallback)

    Returns (description_string, flags_dict).
    """
    try:
        with open(path, "r", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= 50:  # Check first 50 lines for protocol headers
                    break
                lines.append(line.rstrip())
    except OSError:
        return "", {}

    # --- Pass 1: Protocol headers ---
    description = ""
    usage = ""
    purpose = ""
    flags: dict[str, str] = {}

    for line in lines:
        m = PROTOCOL_DESC.match(line)
        if m:
            description = m.group(1).strip()
            continue
        m = PROTOCOL_USAGE.match(line)
        if m:
            usage = m.group(1).strip()
            continue
        m = PROTOCOL_PURPOSE.match(line)
        if m:
            purpose = m.group(1).strip()
            continue
        m = PROTOCOL_FLAG.match(line)
        if m:
            flag_text = m.group(1).strip()
            # "#@ Flag: -w, --wipe: Wipe userdata" → {"-w, --wipe": "Wipe userdata"}
            parts = flag_text.split(":", 1)
            flag_name = parts[0].strip()
            flag_desc = parts[1].strip() if len(parts) > 1 else ""
            flags[flag_name] = flag_desc
            continue

    if description:
        parts = [description]
        if usage:
            parts.append(f"Usage: {usage}")
        if purpose:
            parts.append(f"Purpose: {purpose}")
        return " | ".join(parts), flags

    # --- Pass 2: Legacy fallbacks ---
    for line in lines:
        for pattern in LEGACY_PATTERNS:
            m = pattern.match(line)
            if m:
                desc = m.group(1).strip()
                if desc and not desc.startswith("!") and len(desc) > 5:
                    return desc, flags

    return "", flags


def _scan_single_directory(db: Database, directory: Path) -> int:
    """Scan one directory for executable scripts and add them to Copa.

    Returns number of scripts added.
    """
    if not directory.is_dir():
        return 0

    added = 0
    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        return 0

    for entry in entries:
        try:
            is_file = entry.is_file()
            is_exec = os.access(entry, os.X_OK)
        except (PermissionError, OSError):
            continue

        if is_file and is_exec:
            name = entry.name
            # Skip hidden files and common non-script files
            if name.startswith(".") or name.endswith((".md", ".txt", ".log")):
                continue

            description, flags = extract_description(entry)
            if not db.command_exists(name):
                db.add_command(
                    command=name,
                    description=description,
                    source="scan",
                    flags=flags if flags else None,
                )
                added += 1

    return added


def scan_directory(db: Database, directory: Path | None = None) -> int:
    """Scan directories for executable scripts and add them to Copa.

    If directory is given, scans only that directory.
    Otherwise, scans all directories on $PATH.

    Returns number of scripts added.
    """
    if directory is not None:
        return _scan_single_directory(db, directory)

    # Default: scan all $PATH directories
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    added = 0
    for dir_str in path_dirs:
        d = Path(dir_str)
        if d.is_dir():
            added += _scan_single_directory(db, d)
    return added
