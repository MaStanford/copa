"""Click CLI for Copa — Command Palette."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import click

from .db import Database
from .models import Command, CopaFile
from .scoring import rank_commands


def get_db() -> Database:
    db = Database()
    db.init_db()
    return db


# --- Main group ---

@click.group()
@click.version_option(package_name="copa")
def cli():
    """Copa — Command Palette. Smart command tracking, ranking, and sharing."""
    pass


# --- add ---

@cli.command()
@click.argument("command")
@click.option("-d", "--description", default="", help="Description of the command.")
@click.option("-g", "--group", default=None, help="Group name.")
@click.option("-t", "--tag", multiple=True, help="Tags (can be repeated).")
@click.option("-p", "--pin", is_flag=True, help="Pin this command.")
def add(command: str, description: str, group: str | None, tag: tuple[str, ...], pin: bool):
    """Save a command with optional description and group."""
    db = get_db()
    cmd_id = db.add_command(
        command=command,
        description=description,
        group_name=group,
        tags=list(tag) if tag else None,
    )
    if pin:
        db.pin_command(cmd_id, True)
    click.echo(f"Added [{cmd_id}]: {command}")
    if description:
        click.echo(f"  → {description}")
    if group:
        click.echo(f"  group: {group}")


# --- list ---

@cli.command("list")
@click.option("-g", "--group", default=None, help="Filter by group.")
@click.option("-n", "--limit", default=20, help="Number of commands to show.")
@click.option("-s", "--source", default=None, help="Filter by source.")
@click.option("--needs-desc", is_flag=True, help="Show only commands needing description.")
def list_cmd(group: str | None, limit: int, source: str | None, needs_desc: bool):
    """List commands ranked by score."""
    db = get_db()
    commands = db.list_commands(
        group_name=group,
        limit=limit,
        source=source,
        needs_description=True if needs_desc else None,
    )
    ranked = rank_commands(commands)
    if not ranked:
        click.echo("No commands found.")
        return

    for cmd in ranked:
        badge = ""
        if cmd.shared_set:
            badge = click.style(f" [shared:{cmd.shared_set}]", fg="cyan")
        elif cmd.group_name:
            badge = click.style(f" [{cmd.group_name}]", fg="magenta")
        if cmd.is_pinned:
            badge += click.style(" [pinned]", fg="yellow")

        desc = ""
        if cmd.description:
            desc = click.style(f" — {cmd.description}", dim=True)

        freq = click.style(f" ({cmd.frequency}×)", dim=True)
        score_str = click.style(f" s={cmd.score:.1f}", dim=True)

        click.echo(f"  [{cmd.id:>4}] {cmd.command}{desc}{badge}{freq}{score_str}")


# --- search ---

@cli.command()
@click.argument("query")
@click.option("-g", "--group", default=None, help="Filter by group.")
@click.option("-n", "--limit", default=20, help="Max results.")
def search(query: str, group: str | None, limit: int):
    """Search commands by keyword (FTS)."""
    db = get_db()
    commands = db.search_commands(query, group_name=group, limit=limit)
    ranked = rank_commands(commands)
    if not ranked:
        click.echo(f"No commands matching '{query}'.")
        return

    for cmd in ranked:
        badge = ""
        if cmd.group_name:
            badge = click.style(f" [{cmd.group_name}]", fg="magenta")
        desc = ""
        if cmd.description:
            desc = click.style(f" — {cmd.description}", dim=True)
        click.echo(f"  [{cmd.id:>4}] {cmd.command}{desc}{badge}")


# --- remove ---

@cli.command()
@click.argument("cmd_id", type=int)
def remove(cmd_id: int):
    """Remove a command by ID."""
    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)
    db.remove_command(cmd_id)
    click.echo(f"Removed [{cmd_id}]: {cmd.command}")


# --- stats ---

@cli.command()
def stats():
    """Show usage statistics."""
    db = get_db()
    s = db.get_stats()
    click.echo(f"Commands:     {s['total_commands']}")
    click.echo(f"Total uses:   {s['total_uses']}")
    click.echo(f"Groups:       {s['total_groups']}")
    click.echo(f"Shared sets:  {s['shared_sets']}")
    click.echo(f"Pinned:       {s['pinned']}")
    click.echo(f"Need desc:    {s['needs_description']}")
    if s.get("by_source"):
        click.echo("By source:")
        for source, count in s["by_source"].items():
            click.echo(f"  {source}: {count}")


# --- sync ---

@cli.command()
@click.option("--history", type=click.Path(exists=True), default=None, help="Path to zsh history file.")
def sync(history: str | None):
    """Backfill from ~/.zsh_history."""
    from .history import sync_history

    db = get_db()
    history_path = Path(history) if history else None
    added = sync_history(db, history_path)
    click.echo(f"Synced: {added} new commands from history.")


# --- scan ---

@cli.command()
@click.option("--dir", "directory", type=click.Path(exists=True), default=None,
              help="Directory to scan (default: ~/bin).")
def scan(directory: str | None):
    """Import ~/bin/ script metadata."""
    from .scanner import scan_directory

    db = get_db()
    dir_path = Path(directory) if directory else None
    added = scan_directory(db, dir_path)
    click.echo(f"Scanned: {added} scripts added.")


# --- evolve ---

@cli.command()
@click.option("-k", "--top-k", default=20, help="Number of top commands to add.")
def evolve(top_k: int):
    """Auto-add top-K frequent history commands."""
    from .evolve import evolve as do_evolve

    db = get_db()
    added = do_evolve(db, top_k)
    if not added:
        click.echo("No new commands to evolve.")
        return
    click.echo(f"Added {len(added)} commands (needs_description=1):")
    for cmd in added:
        click.echo(f"  + {cmd}")
    click.echo("\nRun 'copa fix' to add descriptions.")


# --- fix ---

@cli.command()
def fix():
    """Interactively add descriptions to undescribed commands."""
    db = get_db()
    commands = db.list_commands(needs_description=True, limit=100)
    if not commands:
        click.echo("All commands have descriptions.")
        return

    click.echo(f"{len(commands)} commands need descriptions. (Enter to skip, 'q' to quit)\n")
    fixed = 0
    for cmd in commands:
        click.echo(f"  [{cmd.id}] {click.style(cmd.command, bold=True)}")
        desc = input("  Description: ").strip()
        if desc.lower() == "q":
            break
        if desc:
            db.update_description(cmd.id, desc)
            fixed += 1
            click.echo(click.style(f"  ✓ saved", fg="green"))
        click.echo()

    click.echo(f"Fixed {fixed} descriptions.")


# --- import ---

@cli.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("-g", "--group", default=None, help="Group name for imported commands.")
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


# --- share subgroup ---

@cli.group()
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


# --- Hidden internal commands ---

@cli.command("_record", hidden=True)
@click.argument("command")
def record(command: str):
    """Record a command usage (called by precmd hook)."""
    db = get_db()
    db.record_usage(command)


@cli.command("_init", hidden=True)
def init():
    """Initialize the Copa database."""
    db = get_db()
    click.echo("Copa database initialized.")


@cli.command("fzf-list", hidden=True)
@click.option("--mode", default="all", type=click.Choice(["all", "frequent", "recent", "group"]))
@click.option("--group", default=None)
def fzf_list_cmd(mode: str, group: str | None):
    """Output formatted lines for fzf."""
    from .fzf import fzf_list

    db = get_db()
    lines = fzf_list(db, mode=mode, group=group)
    for line in lines:
        click.echo(line)


@cli.command("_preview", hidden=True)
@click.argument("cmd_id", type=int)
def preview(cmd_id: int):
    """Rich preview for fzf preview pane."""
    from .fzf import format_preview

    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.")
        return
    from .scoring import compute_score
    cmd.score = compute_score(cmd)
    click.echo(format_preview(cmd))


@cli.command("mcp", hidden=True)
def mcp_cmd():
    """Run the MCP server (stdio transport)."""
    from .mcp_server import main
    main()


if __name__ == "__main__":
    cli()
