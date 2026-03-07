"""Shared command set management."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from .db import Database
from .models import CopaFile, SharedSet


def find_fbsource_root() -> Path | None:
    """Find the fbsource checkout root."""
    # Check env var first
    env_root = os.environ.get("FBSOURCE_ROOT")
    if env_root:
        p = Path(env_root)
        if p.is_dir():
            return p

    # Try hg root from common locations
    for candidate in [Path.home() / "fbsource", Path("/data/users") / os.getenv("USER", "") / "fbsource"]:
        if candidate.is_dir():
            return candidate

    # Try hg root
    try:
        result = subprocess.run(
            ["hg", "root"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            p = Path(result.stdout.strip())
            if p.is_dir():
                return p
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def resolve_copa_path(source: str) -> Path | None:
    """Resolve a .copa source path.

    Accepts:
    - Absolute/relative file paths
    - fbsource-relative paths (e.g., arvr/agios/supra/SupraCommands)
    """
    # Direct file path
    p = Path(source).expanduser()
    if p.exists():
        return p

    # Add .copa extension if missing
    if not source.endswith(".copa"):
        p_ext = Path(source + ".copa").expanduser()
        if p_ext.exists():
            return p_ext

    # fbsource-relative
    root = find_fbsource_root()
    if root:
        fbpath = root / source
        if fbpath.exists():
            return fbpath
        if not source.endswith(".copa"):
            fbpath_ext = root / (source + ".copa")
            if fbpath_ext.exists():
                return fbpath_ext

    return None


def load_copa_file(path: Path) -> CopaFile:
    """Load a .copa JSON file."""
    data = json.loads(path.read_text())
    return CopaFile.from_dict(data)


def export_group(db: Database, group_name: str, author: str = "") -> CopaFile:
    """Export a group as a CopaFile."""
    commands = db.list_commands(group_name=group_name, limit=10000)
    copa_file = CopaFile(
        name=group_name,
        description=f"Exported from Copa group '{group_name}'",
        author=author,
        commands=[cmd.to_dict() for cmd in commands],
    )
    return copa_file


def import_shared_set(db: Database, copa_file: CopaFile, source_path: str | None = None) -> int:
    """Import commands from a CopaFile into the database.

    Returns number of commands imported.
    """
    # Register the shared set
    ss = SharedSet(
        name=copa_file.name,
        description=copa_file.description,
        source_path=source_path,
        loaded_at=time.time(),
        version=copa_file.copa_version,
        author=copa_file.author,
    )
    db.upsert_shared_set(ss)

    count = 0
    for cmd_data in copa_file.commands:
        command = cmd_data.get("command", "").strip()
        if not command:
            continue
        description = cmd_data.get("description", "")
        tags = cmd_data.get("tags", [])

        db.add_command(
            command=command,
            description=description,
            source="shared",
            group_name=copa_file.name,
            shared_set=copa_file.name,
            tags=tags,
        )
        count += 1

    return count


def sync_directory(db: Database, directory: str) -> dict[str, int]:
    """Sync all .copa files from a directory tree.

    Returns dict of {filename: commands_imported}.
    """
    path = resolve_copa_path(directory)
    if not path or not path.is_dir():
        return {}

    results = {}
    for copa_path in sorted(path.rglob("*.copa")):
        try:
            copa_file = load_copa_file(copa_path)
            count = import_shared_set(db, copa_file, source_path=str(copa_path))
            results[copa_path.name] = count
        except (json.JSONDecodeError, KeyError) as e:
            results[copa_path.name] = -1  # error indicator

    return results
