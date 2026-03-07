"""FastMCP server for Copa — exposes commands to Claude Code."""

from __future__ import annotations

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

    return mcp


def main():
    """Run the MCP server."""
    mcp = create_mcp_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
