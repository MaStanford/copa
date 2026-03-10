"""Click CLI for Copa — Command Palette."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .cli_common import complete_group, complete_shared_set, complete_source, get_db
from .scoring import rank_commands


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
@click.option("-g", "--group", default=None, help="Group name.", shell_complete=complete_group)
@click.option("-t", "--tag", multiple=True, help="Tags (can be repeated).")
@click.option("-p", "--pin", is_flag=True, help="Pin this command.")
@click.option("-f", "--flag", multiple=True,
              help="Flag docs as 'flag: description' (repeatable).")
def add(command: str, description: str, group: str | None, tag: tuple[str, ...],
        pin: bool, flag: tuple[str, ...]):
    """Save a command with optional description and group."""
    db = get_db()

    # Parse --flag options into a dict
    flags: dict[str, str] = {}
    for f in flag:
        parts = f.split(":", 1)
        flag_name = parts[0].strip()
        flag_desc = parts[1].strip() if len(parts) > 1 else ""
        flags[flag_name] = flag_desc

    cmd_id = db.add_command(
        command=command,
        description=description,
        group_name=group,
        tags=list(tag) if tag else None,
        flags=flags if flags else None,
    )
    if pin:
        db.pin_command(cmd_id, True)
    click.echo(f"Added [{cmd_id}]: {command}")
    if description:
        click.echo(f"  → {description}")
    if flags:
        click.echo(f"  flags: {len(flags)} documented")
    if group:
        click.echo(f"  group: {group}")


# --- list ---

@cli.command("list")
@click.option("-g", "--group", default=None, help="Filter by group.", shell_complete=complete_group)
@click.option("-n", "--limit", default=20, help="Number of commands to show.")
@click.option("-s", "--source", default=None, help="Filter by source.", shell_complete=complete_source)
@click.option("--set", "shared_set", default=None, help="Filter by shared set.", shell_complete=complete_shared_set)
@click.option("--needs-desc", is_flag=True, help="Show only commands needing description.")
def list_cmd(group: str | None, limit: int, source: str | None, shared_set: str | None, needs_desc: bool):
    """List commands ranked by score."""
    db = get_db()
    commands = db.list_commands(
        group_name=group,
        limit=limit,
        source=source,
        needs_description=True if needs_desc else None,
        shared_set=shared_set,
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
@click.option("-g", "--group", default=None, help="Filter by group.", shell_complete=complete_group)
@click.option("-s", "--source", default=None, help="Filter by source.", shell_complete=complete_source)
@click.option("--set", "shared_set", default=None, help="Filter by shared set.", shell_complete=complete_shared_set)
@click.option("-n", "--limit", default=20, help="Max results.")
def search(query: str, group: str | None, source: str | None, shared_set: str | None, limit: int):
    """Search commands by keyword (FTS)."""
    db = get_db()
    commands = db.search_commands(query, group_name=group, source=source, shared_set=shared_set, limit=limit)
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
              help="Directory to scan (default: all $PATH directories).")
def scan(directory: str | None):
    """Import script metadata from $PATH (supports #@ Description/Usage headers)."""
    from .scanner import scan_directory

    db = get_db()
    dir_path = Path(directory) if directory else None
    added = scan_directory(db, dir_path)
    click.echo(f"Scanned: {added} scripts added.")


# --- Register extracted command modules ---

from . import cli_internal, cli_llm, cli_share

cli_llm.register(cli)
cli_share.register(cli)
cli_internal.register(cli)


if __name__ == "__main__":
    cli()
