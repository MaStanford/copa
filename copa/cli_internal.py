"""Hidden/internal CLI commands for Copa shell integration."""

from __future__ import annotations

import sys

import click

from .cli_common import _close_tty, _open_tty, complete_group, complete_shared_set, get_db


@click.command("_record", hidden=True)
@click.argument("command")
def record(command: str):
    """Record a command usage (called by precmd hook)."""
    db = get_db()
    db.record_usage(command)


@click.command("_init", hidden=True)
def init():
    """Initialize the Copa database."""
    get_db()
    click.echo("Copa database initialized.")


@click.command("fzf-list", hidden=True)
@click.option("--mode", default="all", type=click.Choice(["all", "frequent", "recent", "group", "set"]))
@click.option("--group", default=None, shell_complete=complete_group)
@click.option("--set", "shared_set", default=None, help="Filter by shared set.", shell_complete=complete_shared_set)
def fzf_list_cmd(mode: str, group: str | None, shared_set: str | None):
    """Output formatted lines for fzf."""
    from .fzf import fzf_list

    db = get_db()
    lines = fzf_list(db, mode=mode, group=group, shared_set=shared_set)
    for line in lines:
        click.echo(line)


@click.command("_preview", hidden=True)
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


@click.command("_set-group", hidden=True)
@click.argument("cmd_id", type=int)
def set_group(cmd_id: int):
    """Assign or change the group for a command (called by fzf execute binding)."""
    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)

    tty, old_attrs = _open_tty()

    def tty_write(msg: str):
        if tty:
            tty.write(msg + "\n")
            tty.flush()
        else:
            click.echo(msg)

    def tty_read(prompt: str) -> str:
        if tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().rstrip("\n")
        return input(prompt)

    tty_write(f"  Command: {cmd.command}")
    current = cmd.group_name or "(none)"
    tty_write(f"  Current group: {current}")

    groups = db.get_groups()
    if groups:
        tty_write(f"  Existing groups: {', '.join(groups)}")

    try:
        name = tty_read("  Group name (empty=clear, q=cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        _close_tty(tty, old_attrs)
        return

    if name.lower() == "q":
        _close_tty(tty, old_attrs)
        return

    group_name = name if name else None
    ok = db.update_group(cmd.id, group_name)
    if ok:
        label = group_name or "(none)"
        tty_write(click.style(f"  → group set to: {label}", fg="green"))
    else:
        tty_write(click.style(f"  ✗ command already exists in group '{group_name}'", fg="red"))

    _close_tty(tty, old_attrs)


@click.command("_set-flags", hidden=True)
@click.argument("cmd_id", type=int)
def set_flags(cmd_id: int):
    """Add or edit flags for a command (called by fzf execute binding)."""
    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)

    tty, old_attrs = _open_tty()

    def tty_write(msg: str):
        if tty:
            tty.write(msg + "\n")
            tty.flush()
        else:
            click.echo(msg)

    def tty_read(prompt: str) -> str:
        if tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().rstrip("\n")
        return input(prompt)

    tty_write(f"  Command: {cmd.command}")

    flags = dict(cmd.flags)  # copy existing flags

    if flags:
        tty_write("  Current flags:")
        for flag, desc in flags.items():
            tty_write(f"    {flag}: {desc}")
    else:
        tty_write("  No flags yet.")

    tty_write("  Add flags (empty flag name = done, q = cancel):")

    try:
        while True:
            flag_name = tty_read("  Flag name: ").strip()
            if not flag_name:
                break
            if flag_name.lower() == "q":
                _close_tty(tty, old_attrs)
                return
            flag_desc = tty_read("  Description: ").strip()
            flags[flag_name] = flag_desc
            tty_write(click.style(f"    + {flag_name}: {flag_desc}", fg="green"))
    except (EOFError, KeyboardInterrupt):
        _close_tty(tty, old_attrs)
        return

    if flags != cmd.flags:
        db.update_flags(cmd.id, flags)
        tty_write(click.style(f"  → {len(flags)} flag(s) saved", fg="green"))
    else:
        tty_write("  No changes.")

    _close_tty(tty, old_attrs)


@click.command("_list-groups", hidden=True)
def list_groups():
    """Output group names for fzf group picker (delimited for --with-nth)."""
    db = get_db()
    click.echo("0┃(all)┃")
    for g in db.get_groups():
        click.echo(f"0┃{g}┃")


@click.command("_list-groups-for-assign", hidden=True)
def list_groups_for_assign():
    """Output group names for group-assign modal (delimited for --with-nth)."""
    db = get_db()
    click.echo("0┃(none)┃")
    for g in db.get_groups():
        click.echo(f"0┃{g}┃")


@click.command("_set-group-direct", hidden=True)
@click.argument("cmd_id", type=int)
@click.argument("group_name", required=False, default=None)
def set_group_direct(cmd_id, group_name):
    """Assign group non-interactively (for fzf modal)."""
    db = get_db()
    if group_name == "(none)":
        group_name = None
    db.update_group(cmd_id, group_name)


@click.command("_next-group", hidden=True)
@click.argument("current", default="(all)")
def next_group(current: str):
    """Output the next group in the cycle: (all) → g1 → g2 → ... → (all)."""
    db = get_db()
    groups = ["(all)"] + db.get_groups()
    try:
        idx = groups.index(current)
    except ValueError:
        idx = -1
    next_idx = (idx + 1) % len(groups)
    click.echo(groups[next_idx])


@click.command("_complete-word", hidden=True)
@click.argument("words", nargs=-1)
def complete_word(words):
    """Return tab-completion candidates for a partial command line."""
    if not words:
        return

    db = get_db()

    # All words except the last form the prefix; the last word is the incomplete token
    if len(words) == 1:
        # Single word: return unique first words from all commands matching the token
        token = words[0]
        cur = db.conn.cursor()
        cur.execute("SELECT command, frequency FROM commands ORDER BY frequency DESC")
        seen: set[str] = set()
        for row in cur.fetchall():
            first_word = row["command"].split()[0] if row["command"].split() else ""
            if first_word and first_word.startswith(token) and first_word not in seen:
                seen.add(first_word)
                click.echo(first_word)
        return

    prefix_words = list(words[:-1])
    token = words[-1]

    # Build a LIKE pattern from the prefix words
    # Escape SQL LIKE wildcards in prefix
    prefix = " ".join(prefix_words)
    escaped_prefix = prefix.replace("%", "\\%").replace("_", "\\_")
    like_pattern = escaped_prefix + " %"

    cur = db.conn.cursor()
    cur.execute(
        "SELECT command, frequency FROM commands WHERE command LIKE ? ESCAPE '\\' ORDER BY frequency DESC",
        (like_pattern,),
    )

    word_pos = len(prefix_words)
    seen: set[str] = set()
    for row in cur.fetchall():
        parts = row["command"].split()
        if len(parts) > word_pos:
            candidate = parts[word_pos]
            if candidate.startswith(token) and candidate not in seen:
                seen.add(candidate)
                click.echo(candidate)


@click.command("mcp", hidden=True)
def mcp_cmd():
    """Run the MCP server (stdio transport)."""
    from .mcp_server import main

    main()


@click.command(hidden=True)
@click.argument("shell", type=click.Choice(["zsh", "bash", "fish"]))
def completion(shell: str):
    """Output shell completion script."""
    import os
    import subprocess

    env = os.environ.copy()
    env["_COPA_COMPLETE"] = f"{shell}_source"
    result = subprocess.run(["copa"], env=env, capture_output=True, text=True)
    click.echo(result.stdout)


@click.command("_fzf-config", hidden=True)
def fzf_config_cmd():
    """Output zsh keybinding config for fzf."""
    from .config import emit_zsh_config, load_config

    config = load_config()
    click.echo(emit_zsh_config(config))


@click.command("_batch-group", hidden=True)
@click.argument("cmd_ids", nargs=-1, type=int)
def batch_group(cmd_ids):
    """Batch assign group to multiple commands."""
    if not cmd_ids:
        return
    db = get_db()
    tty, old_attrs = _open_tty()

    def tty_write(msg: str):
        if tty:
            tty.write(msg + "\n")
            tty.flush()
        else:
            click.echo(msg)

    def tty_read(prompt: str) -> str:
        if tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().rstrip("\n")
        return input(prompt)

    tty_write(f"  Batch group: {len(cmd_ids)} command(s)")
    groups = db.get_groups()
    if groups:
        tty_write(f"  Existing groups: {', '.join(groups)}")

    try:
        name = tty_read("  Group name (empty=clear, q=cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        _close_tty(tty, old_attrs)
        return

    if name.lower() == "q":
        _close_tty(tty, old_attrs)
        return

    group_name = name if name else None
    updated = 0
    for cid in cmd_ids:
        if db.update_group(cid, group_name):
            updated += 1

    label = group_name or "(none)"
    tty_write(f"  → {updated}/{len(cmd_ids)} set to: {label}")
    _close_tty(tty, old_attrs)


@click.command("_batch-delete", hidden=True)
@click.argument("cmd_ids", nargs=-1, type=int)
def batch_delete(cmd_ids):
    """Batch delete multiple commands."""
    if not cmd_ids:
        return
    db = get_db()
    tty, old_attrs = _open_tty()

    def tty_write(msg: str):
        if tty:
            tty.write(msg + "\n")
            tty.flush()
        else:
            click.echo(msg)

    def tty_read(prompt: str) -> str:
        if tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().rstrip("\n")
        return input(prompt)

    tty_write(f"  Batch delete: {len(cmd_ids)} command(s)")

    try:
        confirm = tty_read("  Confirm delete? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        _close_tty(tty, old_attrs)
        return

    if confirm != "y":
        tty_write("  cancelled")
        _close_tty(tty, old_attrs)
        return

    removed = 0
    for cid in cmd_ids:
        if db.remove_command(cid):
            removed += 1

    tty_write(f"  → deleted {removed}/{len(cmd_ids)}")
    _close_tty(tty, old_attrs)


@click.command("_batch-describe", hidden=True)
@click.argument("cmd_ids", nargs=-1, type=int)
def batch_describe(cmd_ids):
    """Batch auto-describe commands with LLM."""
    if not cmd_ids:
        return
    from .llm import generate_description

    db = get_db()
    tty, old_attrs = _open_tty()

    def tty_write(msg: str):
        if tty:
            tty.write(msg + "\n")
            tty.flush()
        else:
            click.echo(msg)

    backend = db.get_meta("llm_backend") or "claude"
    model = db.get_meta("ollama_model") or "llama3.2:3b"
    tty_write(f"  Batch describe: {len(cmd_ids)} command(s) ({backend})")

    described = 0
    for cid in cmd_ids:
        cmd = db.get_command(cid)
        if not cmd:
            continue
        tty_write(f"  [{cmd.id}] {cmd.command}")
        desc = generate_description(cmd.command, backend=backend, model=model)
        if desc:
            db.update_description(cmd.id, desc)
            described += 1
            tty_write(f"    → {desc}")
        else:
            tty_write("    → (no suggestion)")

    tty_write(f"  Done: {described}/{len(cmd_ids)} described")
    _close_tty(tty, old_attrs)


def register(cli):
    """Register internal commands with the CLI group."""
    cli.add_command(record)
    cli.add_command(init)
    cli.add_command(fzf_list_cmd)
    cli.add_command(preview)
    cli.add_command(set_group)
    cli.add_command(set_flags)
    cli.add_command(list_groups)
    cli.add_command(list_groups_for_assign)
    cli.add_command(set_group_direct)
    cli.add_command(next_group)
    cli.add_command(complete_word)
    cli.add_command(mcp_cmd)
    cli.add_command(completion)
    cli.add_command(fzf_config_cmd)
    cli.add_command(batch_group)
    cli.add_command(batch_delete)
    cli.add_command(batch_describe)
