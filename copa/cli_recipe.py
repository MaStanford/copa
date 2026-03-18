"""CLI commands for Copa recipes — multi-step command sequences."""

from __future__ import annotations

import json
import subprocess
import sys

import click

from .cli_common import complete_group, get_db


@click.group("recipe")
def recipe_group():
    """Manage multi-step command recipes."""
    pass


@recipe_group.command("list")
@click.option("-g", "--group", default=None, help="Filter by group.", shell_complete=complete_group)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def recipe_list(group: str | None, as_json: bool):
    """List all recipes."""
    db = get_db()
    recipes = db.list_recipes(group_name=group)
    if not recipes:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No recipes found.")
        return

    if as_json:
        click.echo(json.dumps([r.to_dict() for r in recipes], indent=2))
        return

    for r in recipes:
        badge = ""
        if r.group_name:
            badge = click.style(f" [{r.group_name}]", fg="magenta")
        if r.shared_set:
            badge = click.style(f" [shared:{r.shared_set}]", fg="cyan")
        desc = ""
        if r.description:
            desc = click.style(f" — {r.description}", dim=True)
        steps = click.style(f" ({len(r.steps)} steps)", dim=True)
        runs = click.style(f" {r.run_count}×", dim=True) if r.run_count else ""
        click.echo(f"  [{r.id:>4}] {r.name}{desc}{badge}{steps}{runs}")


@recipe_group.command("show")
@click.argument("name")
def recipe_show(name: str):
    """Show a recipe's steps."""
    db = get_db()
    recipe = db.get_recipe_by_name(name)
    if not recipe:
        # Try by ID
        try:
            recipe = db.get_recipe(int(name))
        except ValueError:
            pass
    if not recipe:
        click.echo(f"Recipe '{name}' not found.", err=True)
        sys.exit(1)

    click.echo(click.style(recipe.name, bold=True))
    if recipe.description:
        click.echo(f"  {recipe.description}")
    if recipe.group_name:
        click.echo(click.style(f"  group: {recipe.group_name}", fg="magenta"))
    click.echo()
    for step in recipe.steps:
        num = click.style(f"  {step.step_order}.", bold=True)
        desc = click.style(f"  # {step.description}", dim=True) if step.description else ""
        click.echo(f"{num} {step.command}{desc}")


@recipe_group.command("add")
@click.argument("name")
@click.option("-d", "--description", default="", help="Recipe description.")
@click.option("-g", "--group", default=None, help="Group name.", shell_complete=complete_group)
@click.option(
    "-s", "--step", multiple=True, required=True,
    help="Step as 'command' or 'command :: description' (repeatable).",
)
def recipe_add(name: str, description: str, group: str | None, step: tuple[str, ...]):
    """Create a recipe from ordered steps.

    Example: copa recipe add deploy -s 'npm run build' -s 'docker build -t app .' -s 'docker push app'

    Add descriptions with ::  copa recipe add deploy -s 'npm run build :: Build the project'
    """
    db = get_db()

    if db.get_recipe_by_name(name):
        click.echo(f"Recipe '{name}' already exists. Remove it first or choose another name.", err=True)
        sys.exit(1)

    steps: list[tuple[str, str]] = []
    for s in step:
        if " :: " in s:
            cmd, desc = s.split(" :: ", 1)
        else:
            cmd, desc = s, ""
        steps.append((cmd.strip(), desc.strip()))

    recipe_id = db.add_recipe(name, steps, description=description, group_name=group)
    click.echo(f"Created recipe [{recipe_id}]: {name} ({len(steps)} steps)")
    for i, (cmd, desc) in enumerate(steps, 1):
        d = click.style(f"  # {desc}", dim=True) if desc else ""
        click.echo(f"  {i}. {cmd}{d}")


@recipe_group.command("remove")
@click.argument("name")
def recipe_remove(name: str):
    """Remove a recipe by name or ID."""
    db = get_db()
    recipe = db.get_recipe_by_name(name)
    if not recipe:
        try:
            recipe = db.get_recipe(int(name))
        except ValueError:
            pass
    if not recipe:
        click.echo(f"Recipe '{name}' not found.", err=True)
        sys.exit(1)

    db.remove_recipe(recipe.id)
    click.echo(f"Removed recipe [{recipe.id}]: {recipe.name}")


@recipe_group.command("run")
@click.argument("name")
@click.option("-n", "--dry-run", is_flag=True, help="Print commands without executing.")
@click.option("--stop-on-error/--no-stop-on-error", default=True, help="Stop if a step fails.")
def recipe_run(name: str, dry_run: bool, stop_on_error: bool):
    """Run a recipe's steps sequentially.

    Example: copa recipe run deploy
    """
    db = get_db()
    recipe = db.get_recipe_by_name(name)
    if not recipe:
        try:
            recipe = db.get_recipe(int(name))
        except ValueError:
            pass
    if not recipe:
        click.echo(f"Recipe '{name}' not found.", err=True)
        sys.exit(1)

    if not recipe.steps:
        click.echo(f"Recipe '{recipe.name}' has no steps.")
        return

    click.echo(click.style(f"Running recipe: {recipe.name}", bold=True))
    if recipe.description:
        click.echo(f"  {recipe.description}")
    click.echo()

    failed = 0
    for step in recipe.steps:
        prefix = click.style(f"[{step.step_order}/{len(recipe.steps)}]", bold=True)
        if dry_run:
            click.echo(f"{prefix} {step.command}")
            continue

        click.echo(f"{prefix} {step.command}")
        result = subprocess.run(step.command, shell=True)
        if result.returncode != 0:
            click.echo(click.style(f"  → step failed (exit {result.returncode})", fg="red"))
            failed += 1
            if stop_on_error:
                click.echo("Stopping (use --no-stop-on-error to continue).")
                sys.exit(result.returncode)
        else:
            click.echo(click.style("  → ok", fg="green"))

    if not dry_run:
        db.record_recipe_run(recipe.id)

    if failed:
        click.echo(f"\n{failed}/{len(recipe.steps)} steps failed.")
    elif not dry_run:
        click.echo(click.style(f"\nAll {len(recipe.steps)} steps complete.", fg="green"))


def register(cli):
    """Register recipe commands with the CLI group."""
    cli.add_command(recipe_group)
