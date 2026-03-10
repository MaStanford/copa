"""LLM-related CLI commands: evolve, configure, describe, fix."""

from __future__ import annotations

import sys

import click

from .cli_common import get_db


@click.command()
@click.option("-k", "--top-k", default=20, help="Number of top commands to add.")
@click.option("--auto", "auto_desc", is_flag=True, help="Auto-generate descriptions with LLM.")
def evolve(top_k: int, auto_desc: bool):
    """Auto-add top-K frequent history commands.

    Use --auto to generate descriptions for added commands in one pass.
    """
    from .evolve import evolve as do_evolve

    db = get_db()
    added = do_evolve(db, top_k)
    if not added:
        click.echo("No new commands to evolve.")
        return
    click.echo(f"Added {len(added)} commands:")
    for cmd in added:
        click.echo(f"  + {cmd}")

    if auto_desc:
        from .llm import generate_description

        backend = db.get_meta("llm_backend") or "claude"
        model = db.get_meta("ollama_model") or "llama3.2:3b"
        click.echo(f"\nGenerating descriptions ({backend})...")

        described = 0
        failed = 0
        for cmd_text in added:
            # Look up the command we just added
            results = db.search_commands(cmd_text, limit=1)
            cmd_obj = next((c for c in results if c.command == cmd_text), None)
            if not cmd_obj:
                failed += 1
                continue

            desc = generate_description(cmd_text, backend=backend, model=model)
            if desc:
                db.update_description(cmd_obj.id, desc)
                described += 1
                click.echo(f"  [{cmd_obj.id}] {click.style(desc, fg='cyan')}")
            else:
                failed += 1

        needs_review = len(added) - described
        click.echo(f"\nAdded {len(added)} commands ({described} with auto-descriptions"
                    f"{f', {needs_review} need manual review' if needs_review else ''}).")
    else:
        click.echo(f"\nRun 'copa fix' to add descriptions.")


@click.command()
def configure():
    """Configure Copa settings (LLM backend for description generation)."""
    db = get_db()

    current_backend = db.get_meta("llm_backend") or "claude"
    click.echo(f"Current LLM backend: {current_backend}")

    backend = click.prompt(
        "Which LLM backend?",
        type=click.Choice(["claude", "ollama"]),
        default=current_backend,
    )

    if backend == "ollama":
        from .llm import check_ollama_available, check_ollama_model

        ready, msg = check_ollama_available()
        if not ready:
            click.echo(click.style(f"  Warning: {msg}", fg="yellow"))
            if not click.confirm("Continue anyway?"):
                return

        current_model = db.get_meta("ollama_model") or "llama3.2:3b"
        model = click.prompt("Ollama model", default=current_model)

        if ready:
            available, models = check_ollama_model(model)
            if not available:
                if models:
                    click.echo(f"  Model '{model}' not found. Available: {', '.join(models)}")
                else:
                    click.echo(f"  Model '{model}' not found.")
                if click.confirm(f"  Pull '{model}' now?"):
                    import subprocess
                    click.echo(f"  Pulling {model}...")
                    subprocess.run(["ollama", "pull", model])

        db.set_meta("ollama_model", model)

    db.set_meta("llm_backend", backend)
    click.echo(click.style(f"Saved: backend={backend}", fg="green"))


@click.command()
@click.argument("cmd_id", type=int)
def describe(cmd_id: int):
    """Generate or update a description for a command using LLM."""
    from .llm import generate_description

    db = get_db()
    cmd = db.get_command(cmd_id)
    if not cmd:
        click.echo(f"Command {cmd_id} not found.", err=True)
        sys.exit(1)

    click.echo(f"  [{cmd.id}] {click.style(cmd.command, bold=True)}")
    if cmd.description:
        click.echo(f"  Current: {cmd.description}")

    backend = db.get_meta("llm_backend") or "claude"
    model = db.get_meta("ollama_model") or "llama3.2:3b"

    click.echo(click.style(f"  Generating ({backend})...", dim=True), nl=False)
    suggestion = generate_description(cmd.command, backend=backend, model=model)

    if suggestion:
        click.echo(f"\r  Suggestion: {click.style(suggestion, fg='cyan')}  ")
        desc = input(f"  Description [{suggestion}]: ").strip()
        if desc.lower() == "q":
            return
        if not desc:
            desc = suggestion
    else:
        click.echo("\r  (no suggestion generated)         ")
        desc = input("  Description: ").strip()
        if not desc:
            return

    db.update_description(cmd.id, desc)
    click.echo(click.style("  saved", fg="green"))


@click.command()
@click.option("--auto", "auto_desc", is_flag=True, help="Use LLM to generate description suggestions.")
def fix(auto_desc: bool):
    """Interactively add descriptions to undescribed commands.

    Use --auto to have an LLM generate suggestions (configure backend with 'copa configure').
    """
    db = get_db()
    commands = db.list_commands(needs_description=True, limit=100)
    if not commands:
        click.echo("All commands have descriptions.")
        return

    if auto_desc:
        from .llm import generate_description

        backend = db.get_meta("llm_backend") or "claude"
        model = db.get_meta("ollama_model") or "llama3.2:3b"
        click.echo(f"Using LLM backend: {backend}")
        click.echo(f"{len(commands)} commands need descriptions. (Enter=accept, type to edit, 'q' to quit)\n")
    else:
        click.echo(f"{len(commands)} commands need descriptions. (Enter to skip, 'q' to quit)\n")

    fixed = 0
    for cmd in commands:
        click.echo(f"  [{cmd.id}] {click.style(cmd.command, bold=True)}")

        suggestion = ""
        if auto_desc:
            click.echo(click.style("  Generating...", dim=True), nl=False)
            suggestion = generate_description(cmd.command, backend=backend, model=model) or ""
            # Clear the "Generating..." text
            click.echo(f"\r  Suggestion: {click.style(suggestion, fg='cyan')}" if suggestion else "\r  (no suggestion generated)")

        if auto_desc and suggestion:
            desc = input(f"  Description [{suggestion}]: ").strip()
            if desc.lower() == "q":
                break
            if not desc:
                desc = suggestion  # Enter accepts the suggestion
        else:
            desc = input("  Description: ").strip()
            if desc.lower() == "q":
                break

        if desc:
            db.update_description(cmd.id, desc)
            fixed += 1
            click.echo(click.style("  saved", fg="green"))
        click.echo()

    click.echo(f"Fixed {fixed} descriptions.")


def register(cli):
    """Register LLM commands with the CLI group."""
    cli.add_command(evolve)
    cli.add_command(configure)
    cli.add_command(describe)
    cli.add_command(fix)
