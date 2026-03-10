"""Share, create, and import CLI commands."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import click

from .cli_common import complete_group, get_db
from .models import CopaFile


@click.command()
@click.option("-g", "--group", default=None, help="Group to export (prompted if omitted).", shell_complete=complete_group)
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file path (default: <group>.copa).")
@click.option("-a", "--author", default="", help="Author name.")
@click.option("-d", "--description", default="", help="Description of the command set.")
def create(group: str | None, output: str | None, author: str, description: str):
    """Create a .copa file, optionally pre-populated from an existing group."""
    db = get_db()

    if group is None:
        groups = db.get_groups()
        if groups:
            click.echo("Existing groups:")
            for g in groups:
                click.echo(f"  - {g}")
        group = click.prompt("Group name")

    commands = db.list_commands(group_name=group, limit=10000)

    if commands:
        copa_file = CopaFile(
            name=group,
            description=description or f"Commands from group '{group}'",
            author=author,
            commands=[cmd.to_dict() for cmd in commands],
        )
    else:
        copa_file = CopaFile(
            name=group,
            description=description or f"Commands for '{group}'",
            author=author,
            commands=[
                {"command": "echo hello", "description": "Example command — replace me", "tags": []},
            ],
        )

    if output is None:
        output = f"{group}.copa"

    path = Path(output)
    path.write_text(json.dumps(copa_file.to_dict(), indent=2) + "\n")

    count = len(copa_file.commands)
    if commands:
        click.echo(f"Created {path} with {count} commands from group '{group}'.")
    else:
        click.echo(f"Created {path} with placeholder template for group '{group}'.")
    click.echo(f"Edit the file, then load with: copa share load {path}")


# --- share subgroup ---

@click.group()
def share():
    """Manage shared command sets."""
    pass


@share.command("export")
@click.argument("group_name")
@click.option("-o", "--output", type=click.Path(), default=None, help="Output file path.")
@click.option("-a", "--author", default="", help="Author name.")
def share_export(group_name: str, output: str | None, author: str):
    """Export a group as a .copa JSON file."""
    from .sharing import export_group

    db = get_db()
    copa_file = export_group(db, group_name, author=author)

    if not copa_file.commands:
        click.echo(f"No commands found in group '{group_name}'.", err=True)
        sys.exit(1)

    if output is None:
        output = f"{group_name}.copa"

    path = Path(output)
    path.write_text(json.dumps(copa_file.to_dict(), indent=2) + "\n")
    click.echo(f"Exported {len(copa_file.commands)} commands to {path}")


@share.command("load")
@click.argument("source")
def share_load(source: str):
    """Load a shared command set from file or fbsource path."""
    from .sharing import import_shared_set, load_copa_file, resolve_copa_path

    path = resolve_copa_path(source)
    if not path:
        click.echo(f"Could not resolve source: {source}", err=True)
        sys.exit(1)

    try:
        copa_file = load_copa_file(path)
    except (json.JSONDecodeError, KeyError) as e:
        click.echo(f"Error parsing {path}: {e}", err=True)
        sys.exit(1)

    db = get_db()
    count = import_shared_set(db, copa_file, source_path=str(path))
    click.echo(f"Loaded '{copa_file.name}': {count} commands from {path}")


@share.command("list")
def share_list():
    """List loaded shared sets."""
    db = get_db()
    sets = db.get_shared_sets()
    if not sets:
        click.echo("No shared sets loaded.")
        return

    for ss in sets:
        loaded = datetime.fromtimestamp(ss.loaded_at).strftime("%Y-%m-%d %H:%M") if ss.loaded_at else "unknown"
        click.echo(f"  {click.style(ss.name, bold=True)}")
        if ss.description:
            click.echo(f"    {ss.description}")
        click.echo(f"    v{ss.version} by {ss.author or '?'} — loaded {loaded}")
        if ss.source_path:
            click.echo(f"    source: {ss.source_path}")
        click.echo()


@share.command("sync")
@click.argument("directory")
def share_sync(directory: str):
    """Sync all .copa files from a directory."""
    from .sharing import sync_directory

    db = get_db()
    results = sync_directory(db, directory)
    if not results:
        click.echo(f"No .copa files found in {directory}.")
        return

    for fname, count in results.items():
        if count < 0:
            click.echo(f"  ✗ {fname} (error)")
        else:
            click.echo(f"  ✓ {fname}: {count} commands")


# --- import ---

@click.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("-g", "--group", default=None, help="Group name for imported commands.", shell_complete=complete_group)
def import_cmd(file: str, group: str | None):
    """Import commands from a markdown file."""
    path = Path(file)
    text = path.read_text()
    db = get_db()

    commands = _parse_markdown(text)
    added = 0
    for cmd_text, desc in commands:
        db.add_command(
            command=cmd_text,
            description=desc,
            source="manual",
            group_name=group,
        )
        added += 1

    click.echo(f"Imported {added} commands from {path.name}.")


def _parse_markdown(text: str) -> list[tuple[str, str]]:
    """Parse commands from markdown. Returns (command, description) tuples."""
    results = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Code block: ```\ncommand\n```
        if line.startswith("```"):
            desc = ""
            # Look backwards for a description header
            if i > 0:
                prev = lines[i - 1].strip()
                if prev and not prev.startswith("```"):
                    desc = prev.lstrip("#").lstrip("0123456789.").strip()

            i += 1
            block_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block_lines.append(lines[i].rstrip())
                i += 1
            cmd = "\n".join(block_lines).strip()
            if cmd:
                results.append((cmd, desc))
            i += 1
            continue

        # Backtick command with -- description: `command` -- description
        m = re.match(r"`([^`]+)`\s*(?:--|—)\s*(.+)", line)
        if m:
            results.append((m.group(1).strip(), m.group(2).strip()))
            i += 1
            continue

        # Numbered list: 1. Description\n   command (next line)
        m = re.match(r"\d+\.\s+(.+)", line)
        if m and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and not re.match(r"\d+\.", next_line):
                # Next line looks like a command
                desc = m.group(1).strip()
                cmd = next_line.strip("`").strip()
                if cmd:
                    results.append((cmd, desc))
                    i += 2
                    continue

        # Bullet with backtick: - `command` description
        m = re.match(r"[-*]\s+`([^`]+)`\s*(.*)", line)
        if m:
            results.append((m.group(1).strip(), m.group(2).strip()))
            i += 1
            continue

        i += 1

    return results


def register(cli):
    """Register share/import commands with the CLI group."""
    cli.add_command(create)
    cli.add_command(share)
    cli.add_command(import_cmd)
