"""FastMCP server for Copa — exposes commands to Claude Code."""

from __future__ import annotations

import json
from pathlib import Path

from .db import Database
from .scoring import rank_commands


def create_mcp_server():
    """Create and configure the FastMCP server."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("Copa")
    db = Database()
    db.init_db()

    @mcp.tool()
    def copa_search(query: str, group: str | None = None, limit: int = 20) -> str:
        """Search Copa commands by keyword. Returns matching commands with descriptions."""
        commands = db.search_commands(query, group_name=group, limit=limit)
        ranked = rank_commands(commands)
        if not ranked:
            return f"No commands found matching '{query}'."
        lines = []
        for cmd in ranked:
            parts = [f"[{cmd.id}] {cmd.command}"]
            if cmd.description:
                parts.append(f"  → {cmd.description}")
            if cmd.group_name:
                parts.append(f"  group: {cmd.group_name}")
            if cmd.tags:
                parts.append(f"  tags: {', '.join(cmd.tags)}")
            lines.append("\n".join(parts))
        return "\n\n".join(lines)

    @mcp.tool()
    def copa_list_commands(group: str | None = None, limit: int = 20) -> str:
        """List Copa commands ranked by usage score. Optionally filter by group."""
        if group:
            commands = db.list_commands(group_name=group, limit=limit)
        else:
            commands = db.list_commands(limit=limit)
        ranked = rank_commands(commands)
        if not ranked:
            return "No commands found."
        lines = []
        for cmd in ranked:
            badge = ""
            if cmd.shared_set:
                badge = " [shared]"
            elif cmd.group_name:
                badge = f" [{cmd.group_name}]"
            desc = f" — {cmd.description}" if cmd.description else ""
            lines.append(f"[{cmd.id}] {cmd.command}{desc}{badge} ({cmd.frequency}×)")
        return "\n".join(lines)

    @mcp.tool()
    def copa_list_groups() -> str:
        """List all Copa command groups."""
        groups = db.get_groups()
        if not groups:
            return "No groups found."
        return "\n".join(f"- {g}" for g in groups)

    @mcp.tool()
    def copa_get_stats() -> str:
        """Get Copa usage statistics."""
        stats = db.get_stats()
        lines = [
            f"Total commands: {stats['total_commands']}",
            f"Total uses: {stats['total_uses']}",
            f"Groups: {stats['total_groups']}",
            f"Shared sets: {stats['shared_sets']}",
            f"Pinned: {stats['pinned']}",
            f"Need description: {stats['needs_description']}",
        ]
        if stats.get("by_source"):
            lines.append("By source:")
            for source, count in stats["by_source"].items():
                lines.append(f"  {source}: {count}")
        return "\n".join(lines)

    @mcp.tool()
    def copa_add_command(
        command: str,
        description: str = "",
        group: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Add a command to Copa with optional description, group, and tags."""
        cmd_id = db.add_command(
            command=command,
            description=description,
            group_name=group,
            tags=tags,
        )
        return f"Added command [{cmd_id}]: {command}"

    @mcp.tool()
    def copa_update_description(command_id: int, description: str) -> str:
        """Update the description of a Copa command."""
        cmd = db.get_command(command_id)
        if not cmd:
            return f"Command {command_id} not found."
        db.update_description(command_id, description)
        return f"Updated [{command_id}] {cmd.command}: {description}"

    @mcp.tool()
    def copa_delete_command(command_id: int) -> str:
        """Delete a command from Copa by its ID."""
        cmd = db.get_command(command_id)
        if not cmd:
            return f"Command {command_id} not found."
        db.remove_command(command_id)
        return f"Deleted [{command_id}] {cmd.command}"

    @mcp.tool()
    def copa_set_group(command_id: int, group: str | None = None) -> str:
        """Set or change the group of a command. Pass group=None to remove from group."""
        cmd = db.get_command(command_id)
        if not cmd:
            return f"Command {command_id} not found."
        db.update_group(command_id, group)
        if group:
            return f"Moved [{command_id}] {cmd.command} to group '{group}'"
        return f"Removed [{command_id}] {cmd.command} from its group"

    @mcp.tool()
    def copa_update_flags(command_id: int, flags: dict[str, str]) -> str:
        """Update the flags/options documentation for a command.

        flags is a dict mapping flag name to description, e.g. {"-v": "Verbose output"}.
        """
        cmd = db.get_command(command_id)
        if not cmd:
            return f"Command {command_id} not found."
        db.update_flags(command_id, flags)
        flag_list = ", ".join(f"{k}: {v}" for k, v in flags.items())
        return f"Updated flags for [{command_id}] {cmd.command}: {flag_list}"

    @mcp.tool()
    def copa_pin_command(command_id: int, pinned: bool = True) -> str:
        """Pin or unpin a command. Pinned commands always appear at the top."""
        cmd = db.get_command(command_id)
        if not cmd:
            return f"Command {command_id} not found."
        db.pin_command(command_id, pinned)
        action = "Pinned" if pinned else "Unpinned"
        return f"{action} [{command_id}] {cmd.command}"

    @mcp.tool()
    def copa_create_group(name: str, commands: list[dict] | None = None) -> str:
        """Create a Copa group and optionally add commands to it.

        Each command in the list should have 'command' and optionally 'description' and 'tags'.
        """
        count = 0
        if commands:
            for cmd_data in commands:
                cmd_text = cmd_data.get("command", "").strip()
                if not cmd_text:
                    continue
                db.add_command(
                    command=cmd_text,
                    description=cmd_data.get("description", ""),
                    group_name=name,
                    tags=cmd_data.get("tags"),
                )
                count += 1
        return f"Group '{name}' created with {count} commands."

    @mcp.tool()
    def copa_bulk_add(commands: list[dict], group: str | None = None) -> str:
        """Bulk add commands to Copa.

        Each item should have 'command' and optionally 'description' and 'tags'.
        """
        count = 0
        for cmd_data in commands:
            cmd_text = cmd_data.get("command", "").strip()
            if not cmd_text:
                continue
            db.add_command(
                command=cmd_text,
                description=cmd_data.get("description", ""),
                group_name=group,
                tags=cmd_data.get("tags"),
            )
            count += 1
        return f"Added {count} commands."

    @mcp.tool()
    def copa_share_load(file_path: str) -> str:
        """Load a .copa file into Copa as a shared set.

        The file_path should be a path to a .copa JSON file.
        """
        from .sharing import import_shared_set, load_copa_file, resolve_copa_path

        resolved = resolve_copa_path(file_path)
        if not resolved or not resolved.is_file():
            return f"File not found: {file_path}"
        copa_file = load_copa_file(resolved)
        count = import_shared_set(db, copa_file, source_path=str(resolved))
        return f"Loaded shared set '{copa_file.name}' with {count} commands from {resolved}"

    @mcp.tool()
    def copa_share_list() -> str:
        """List all loaded shared sets."""
        sets = db.get_shared_sets()
        if not sets:
            return "No shared sets loaded."
        lines = []
        for ss in sets:
            parts = [f"- {ss.name}"]
            if ss.description:
                parts[0] += f": {ss.description}"
            if ss.author:
                parts.append(f"  author: {ss.author}")
            if ss.source_path:
                parts.append(f"  source: {ss.source_path}")
            lines.append("\n".join(parts))
        return "\n".join(lines)

    @mcp.tool()
    def copa_share_remove(name: str) -> str:
        """Remove a shared set and its commands from Copa."""
        sets = db.get_shared_sets()
        if not any(ss.name == name for ss in sets):
            return f"Shared set '{name}' not found."
        db.remove_shared_set(name)
        return f"Removed shared set '{name}'"

    @mcp.tool()
    def copa_export_group(group: str, output_path: str | None = None) -> str:
        """Export a Copa group as a .copa JSON file.

        If output_path is not provided, returns the JSON content directly.
        """
        from .sharing import export_group

        copa_file = export_group(db, group)
        if not copa_file.commands:
            return f"Group '{group}' has no commands to export."
        content = json.dumps(copa_file.to_dict(), indent=2)
        if output_path:
            Path(output_path).write_text(content)
            return f"Exported group '{group}' ({len(copa_file.commands)} commands) to {output_path}"
        return content

    @mcp.tool()
    def copa_recipe_list(group: str | None = None) -> str:
        """List all Copa recipes. Optionally filter by group."""
        recipes = db.list_recipes(group_name=group)
        if not recipes:
            return "No recipes found."
        lines = []
        for r in recipes:
            badge = f" [{r.group_name}]" if r.group_name else ""
            desc = f" — {r.description}" if r.description else ""
            lines.append(f"[{r.id}] {r.name}{desc}{badge} ({len(r.steps)} steps, {r.run_count}×)")
        return "\n".join(lines)

    @mcp.tool()
    def copa_recipe_show(name: str) -> str:
        """Show a recipe's steps by name."""
        recipe = db.get_recipe_by_name(name)
        if not recipe:
            return f"Recipe '{name}' not found."
        lines = [f"Recipe: {recipe.name}"]
        if recipe.description:
            lines.append(f"Description: {recipe.description}")
        if recipe.group_name:
            lines.append(f"Group: {recipe.group_name}")
        lines.append(f"Steps ({len(recipe.steps)}):")
        for step in recipe.steps:
            desc = f"  # {step.description}" if step.description else ""
            lines.append(f"  {step.step_order}. {step.command}{desc}")
        return "\n".join(lines)

    @mcp.tool()
    def copa_recipe_add(
        name: str,
        steps: list[dict],
        description: str = "",
        group: str | None = None,
    ) -> str:
        """Create a Copa recipe from ordered steps.

        Each step should have 'command' and optionally 'description'.
        Example: [{"command": "npm run build"}, {"command": "docker push app", "description": "Push to registry"}]
        """
        step_tuples = [(s.get("command", ""), s.get("description", "")) for s in steps if s.get("command", "").strip()]
        if not step_tuples:
            return "No valid steps provided."
        recipe_id = db.add_recipe(name, step_tuples, description=description, group_name=group)
        return f"Created recipe [{recipe_id}]: {name} ({len(step_tuples)} steps)"

    @mcp.tool()
    def copa_recipe_remove(name: str) -> str:
        """Remove a recipe by name."""
        recipe = db.get_recipe_by_name(name)
        if not recipe:
            return f"Recipe '{name}' not found."
        db.remove_recipe(recipe.id)
        return f"Removed recipe [{recipe.id}]: {recipe.name}"

    return mcp


def main():
    """Run the MCP server."""
    mcp = create_mcp_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
