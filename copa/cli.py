"""Click CLI for Copa — Command Palette."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click

from .cli_common import complete_group, complete_shared_set, complete_source, get_db
from .models import Command
from .scoring import rank_commands


def _cmd_to_json(cmd: Command) -> dict:
    """Convert a Command to a JSON-serializable dict."""
    d: dict = {
        "id": cmd.id,
        "command": cmd.command,
        "description": cmd.description,
        "frequency": cmd.frequency,
        "score": round(cmd.score, 2),
        "source": cmd.source,
    }
    if cmd.group_name:
        d["group"] = cmd.group_name
    if cmd.shared_set:
        d["shared_set"] = cmd.shared_set
    if cmd.is_pinned:
        d["pinned"] = True
    if cmd.tags:
        d["tags"] = cmd.tags
    if cmd.flags:
        d["flags"] = cmd.flags
    return d


# --- Main group ---


@click.group(invoke_without_command=True)
@click.version_option(package_name="copa-cli")
@click.pass_context
def cli(ctx):
    """Copa — Command Palette. Smart command tracking, ranking, and sharing."""
    if ctx.invoked_subcommand is None:
        # Show help, then a setup hint if needed
        click.echo(ctx.get_help())
        _maybe_show_setup_hint()


def _maybe_show_setup_hint():
    """Show a setup hint if Copa is not fully configured."""
    db_path = Path.home() / ".copa" / "copa.db"
    zshrc = Path.home() / ".zshrc"
    has_db = db_path.is_file()
    has_shell = zshrc.is_file() and "copa init zsh" in zshrc.read_text()
    has_fzf = shutil.which("fzf") is not None

    if not has_db or not has_shell or not has_fzf:
        click.echo()
        hint = click.style("  Tip: ", fg="cyan", bold=True)
        hint += "run " + click.style("copa setup", bold=True) + " to get started"
        click.echo(hint)


# --- init ---


@cli.command()
@click.argument("shell", type=click.Choice(["zsh"]))
def init(shell: str):
    """Print shell integration code. Add to your .zshrc: eval "$(copa init zsh)" """
    from importlib.resources import files

    zsh_file = files("copa").joinpath("copa.zsh")
    click.echo(zsh_file.read_text())


# --- setup ---

_SHELL_INTEGRATION_LINE = 'eval "$(copa init zsh)"'


def _write_config_tab_accept(tab_accept: int) -> None:
    """Write or update tab_accept in ~/.copa/config.toml."""
    config_path = Path.home() / ".copa" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.is_file():
        content = config_path.read_text()
    else:
        content = ""

    import re

    if re.search(r"^\[suggest\]", content, re.MULTILINE):
        # [suggest] section exists — update or add tab_accept
        if re.search(r"^tab_accept\s*=", content, re.MULTILINE):
            content = re.sub(
                r"^tab_accept\s*=\s*\d+",
                f"tab_accept = {tab_accept}",
                content,
                flags=re.MULTILINE,
            )
        else:
            content = re.sub(
                r"(\[suggest\]\n)",
                f"\\1tab_accept = {tab_accept}\n",
                content,
            )
    else:
        # No [suggest] section — append it
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"\n[suggest]\ntab_accept = {tab_accept}\n"

    config_path.write_text(content)


@cli.command()
def setup():
    """Interactive setup wizard — checks prerequisites and configures Copa."""
    ok = click.style("OK", fg="green")
    fixed = click.style("FIXED", fg="green")
    skip = click.style("SKIP", fg="yellow")
    fail = click.style("!!", fg="yellow")

    click.echo(click.style("Copa Setup", bold=True))
    click.echo()

    # 1. Check fzf
    if shutil.which("fzf"):
        click.echo(f"  [{ok}] fzf is installed")
    else:
        click.echo(f"  [{fail}] fzf is not installed")
        click.echo("       Copa's Ctrl+R palette requires fzf.")
        click.echo("       Install: " + click.style("brew install fzf", bold=True) + " (macOS)")
        click.echo("                " + click.style("sudo apt install fzf", bold=True) + " (Linux)")
        click.echo()

    # 2. Initialize database
    db_path = Path.home() / ".copa" / "copa.db"
    if db_path.is_file():
        click.echo(f"  [{ok}] Database exists ({db_path})")
    else:
        click.echo(f"  [{fixed}] Database created ({db_path})")
    # Always call get_db to ensure db + tables exist
    from .cli_common import get_db

    get_db()

    # 3. Shell integration
    zshrc = Path.home() / ".zshrc"
    if zshrc.is_file() and _SHELL_INTEGRATION_LINE in zshrc.read_text():
        click.echo(f"  [{ok}] Shell integration in ~/.zshrc")
    else:
        click.echo(f"  [{fail}] Shell integration not found in ~/.zshrc")
        if click.confirm("       Add it now?", default=True):
            with open(zshrc, "a") as f:
                f.write(f"\n# Copa — Command Palette\n{_SHELL_INTEGRATION_LINE}\n")
            click.echo(f"  [{fixed}] Added to ~/.zshrc")
        else:
            click.echo(f"  [{skip}] Skipped — add manually:")
            click.echo(f"       {_SHELL_INTEGRATION_LINE}")

    # 4. Tab completion style
    click.echo()
    click.echo("  Copa shows inline suggestions as you type (ghost text).")
    click.echo("  How should " + click.style("Tab", bold=True) + " handle suggestions?")
    click.echo()
    click.echo("    " + click.style("1", bold=True) + "  " + click.style("Inline accept", fg="cyan"))
    click.echo("       Tab accepts the suggestion directly into your command line.")
    click.echo()
    opt2 = click.style("Menu select", fg="cyan") + click.style(" (default)", dim=True)
    click.echo("    " + click.style("2", bold=True) + "  " + opt2)
    click.echo("       Tab opens a completion menu with the suggestion highlighted.")
    click.echo("       Tab again accepts it. See alternatives before committing.")
    click.echo()
    tab_choice = click.prompt(
        "  Choose tab style",
        type=click.Choice(["1", "2"]),
        default="2",
        show_choices=False,
    )
    tab_accept = int(tab_choice)
    _write_config_tab_accept(tab_accept)
    label = "Inline accept" if tab_accept == 1 else "Menu select"
    click.echo(f"  [{fixed}] Tab style: {label}")

    # 5. Sync history
    click.echo()
    if click.confirm("  Import commands from your zsh history?", default=True):
        from .history import sync_history

        db = get_db()
        added = sync_history(db)
        click.echo(f"  [{fixed}] Synced {added} commands from history")
    else:
        click.echo(f"  [{skip}] Skipped — run " + click.style("copa sync", bold=True) + " later")

    # 6. Done
    click.echo()
    click.echo(click.style("  Setup complete!", fg="green", bold=True))
    click.echo()
    click.echo("  Next steps:")
    click.echo("    " + click.style("source ~/.zshrc", bold=True) + "      Activate Copa in this terminal")
    click.echo("    " + click.style("copa doctor", bold=True) + "          Verify everything is working")
    click.echo("    Press " + click.style("Ctrl+R", bold=True) + "          Open the command palette")
    click.echo("    Type a command + " + click.style("Tab", bold=True) + "    See inline suggestions")
    click.echo()


# --- uninstall ---


@cli.command()
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def uninstall(yes: bool):
    """Remove Copa data and show cleanup instructions."""
    import shutil

    copa_dir = Path.home() / ".copa"

    # Inventory what exists
    items: list[tuple[str, Path]] = []
    if copa_dir.is_dir():
        db_path = copa_dir / "copa.db"
        config_path = copa_dir / "config.toml"
        if db_path.is_file():
            items.append(("database", db_path))
        if config_path.is_file():
            items.append(("config", config_path))
        # Count any other files (.copa exports, etc.)
        other = [f for f in copa_dir.iterdir() if f not in (db_path, config_path)]
        for f in other:
            items.append(("file", f))

    if not items:
        click.echo("No Copa data found (~/.copa/ does not exist or is empty).")
    else:
        click.echo("Copa data directory: ~/.copa/")
        for kind, path in items:
            size = path.stat().st_size if path.is_file() else 0
            label = f"{size:,} bytes" if size else "directory"
            click.echo(f"  {path.name} ({kind}, {label})")

        if not yes:
            click.confirm("\nDelete ~/.copa/ and all its contents?", abort=True)

        shutil.rmtree(copa_dir)
        click.echo(click.style("Deleted ~/.copa/", fg="green"))

    click.echo("\nTo finish uninstalling:")
    click.echo('  1. Remove this line from your ~/.zshrc:  eval "$(copa init zsh)"')
    click.echo("  2. Run:  pip uninstall copa-cli")


# --- add ---


@cli.command()
@click.argument("command")
@click.option("-d", "--description", default="", help="Description of the command.")
@click.option("-g", "--group", default=None, help="Group name.", shell_complete=complete_group)
@click.option("-t", "--tag", multiple=True, help="Tags (can be repeated).")
@click.option("-p", "--pin", is_flag=True, help="Pin this command.")
@click.option("-f", "--flag", multiple=True, help="Flag docs as 'flag: description' (repeatable).")
def add(command: str, description: str, group: str | None, tag: tuple[str, ...], pin: bool, flag: tuple[str, ...]):
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
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_cmd(
    group: str | None,
    limit: int,
    source: str | None,
    shared_set: str | None,
    needs_desc: bool,
    as_json: bool,
):
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
        if as_json:
            click.echo("[]")
        else:
            click.echo("No commands found.")
        return

    if as_json:
        click.echo(json.dumps([_cmd_to_json(c) for c in ranked], indent=2))
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
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def search(query: str, group: str | None, source: str | None, shared_set: str | None, limit: int, as_json: bool):
    """Search commands by keyword (FTS)."""
    db = get_db()
    commands = db.search_commands(query, group_name=group, source=source, shared_set=shared_set, limit=limit)
    ranked = rank_commands(commands)
    if not ranked:
        if as_json:
            click.echo("[]")
        else:
            click.echo(f"No commands matching '{query}'.")
        return

    if as_json:
        click.echo(json.dumps([_cmd_to_json(c) for c in ranked], indent=2))
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
@click.option(
    "--dir",
    "directory",
    type=click.Path(exists=True),
    default=None,
    help="Directory to scan (default: all $PATH directories).",
)
def scan(directory: str | None):
    """Import script metadata from $PATH (supports #@ Description/Usage headers)."""
    from .scanner import scan_directory

    db = get_db()
    dir_path = Path(directory) if directory else None
    added = scan_directory(db, dir_path)
    click.echo(f"Scanned: {added} scripts added.")


# --- pin / unpin ---


@cli.command()
@click.argument("cmd_id", type=int)
def pin(cmd_id: int):
    """Pin a command so it always appears at the top."""
    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)
    db.pin_command(cmd_id, True)
    click.echo(f"Pinned [{cmd_id}]: {cmd.command}")


@cli.command()
@click.argument("cmd_id", type=int)
def unpin(cmd_id: int):
    """Unpin a command."""
    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)
    db.pin_command(cmd_id, False)
    click.echo(f"Unpinned [{cmd_id}]: {cmd.command}")


# --- edit ---


@cli.command()
@click.argument("cmd_id", type=int)
@click.option("-d", "--description", default=None, help="New description.")
@click.option("-g", "--group", default=None, help="New group name (use '' to clear).", shell_complete=complete_group)
@click.option("-f", "--flag", multiple=True, help="Flag docs as 'flag: description' (repeatable, replaces all flags).")
@click.option("-p", "--pin/--no-pin", default=None, help="Pin or unpin the command.")
def edit(cmd_id: int, description: str | None, group: str | None, flag: tuple[str, ...], pin: bool | None):
    """Edit a command's metadata by ID."""
    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)

    changes = []
    if description is not None:
        db.update_description(cmd_id, description)
        changes.append(f"description: {description}")
    if group is not None:
        group_name = group if group else None
        db.update_group(cmd_id, group_name)
        changes.append(f"group: {group_name or '(none)'}")
    if flag:
        flags: dict[str, str] = {}
        for f in flag:
            parts = f.split(":", 1)
            flag_name = parts[0].strip()
            flag_desc = parts[1].strip() if len(parts) > 1 else ""
            flags[flag_name] = flag_desc
        db.update_flags(cmd_id, flags)
        changes.append(f"flags: {len(flags)} documented")
    if pin is not None:
        db.pin_command(cmd_id, pin)
        changes.append("pinned" if pin else "unpinned")

    if not changes:
        click.echo(f"[{cmd_id}] {cmd.command} — nothing to change (use -d, -g, -f, or --pin)")
        return

    click.echo(f"Updated [{cmd_id}]: {cmd.command}")
    for c in changes:
        click.echo(f"  → {c}")


# --- doctor ---


@cli.command()
def doctor():
    """Check Copa setup and diagnose common issues."""
    ok_mark = click.style("OK", fg="green")
    warn_mark = click.style("!!", fg="yellow")
    fail_mark = click.style("FAIL", fg="red")

    click.echo("Copa Doctor\n")

    # 1. Database
    db_path = Path.home() / ".copa" / "copa.db"
    if db_path.is_file():
        size = db_path.stat().st_size
        click.echo(f"  [{ok_mark}] Database: {db_path} ({size:,} bytes)")
        db = get_db()
        s = db.get_stats()
        click.echo(f"       {s['total_commands']} commands, {s['total_groups']} groups, {s['shared_sets']} shared sets")
    else:
        click.echo(f"  [{fail_mark}] Database: not found at {db_path}")
        click.echo("       Run: copa _init")

    # 2. fzf
    if shutil.which("fzf"):
        click.echo(f"  [{ok_mark}] fzf: installed")
    else:
        click.echo(f"  [{fail_mark}] fzf: not found")
        click.echo("       Install: brew install fzf")

    # 3. Shell integration
    zshrc = Path.home() / ".zshrc"
    if zshrc.is_file() and "copa init zsh" in zshrc.read_text():
        click.echo(f"  [{ok_mark}] Shell integration: found in ~/.zshrc")
    else:
        click.echo(f"  [{warn_mark}] Shell integration: not detected in ~/.zshrc")
        click.echo('       Add: eval "$(copa init zsh)"')

    # 4. LLM backend
    if db_path.is_file():
        db = get_db()
        backend = db.get_meta("llm_backend")
        if backend:
            click.echo(f"  [{ok_mark}] LLM backend: {backend}")
            if backend == "ollama":
                model = db.get_meta("ollama_model") or "llama3.2:3b"
                click.echo(f"       Model: {model}")
        else:
            click.echo(f"  [{warn_mark}] LLM backend: not configured")
            click.echo("       Run: copa configure")

    # 5. Completion mode
    config_path = Path.home() / ".copa" / "config.toml"
    if config_path.is_file():
        from .config import load_config

        cfg = load_config(config_path)
        mode = cfg.get("_completion_mode", "fallback")
        click.echo(f"  [{ok_mark}] Completion mode: {mode}")
    else:
        click.echo(f"  [{ok_mark}] Completion mode: fallback (default)")

    click.echo()


# --- Register extracted command modules ---

from . import cli_internal, cli_llm, cli_share

cli_llm.register(cli)
cli_share.register(cli)
cli_internal.register(cli)


if __name__ == "__main__":
    cli()
