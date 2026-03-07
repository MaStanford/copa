# Copa — Command Palette for your shell

Copa tracks the commands you run, ranks them by frequency and recency, and gives you instant fuzzy search via fzf. Think of it as a smart, searchable, shareable upgrade to shell history.

## Features

- **Smart ranking** — commands scored by `2*log(1+freq) + 5*0.5^(age/7d)`, so frequent *and* recent commands float to the top
- **FTS search** — full-text search across commands and their descriptions
- **fzf integration** — Ctrl+R opens a fuzzy-searchable command palette with preview pane
- **Auto-evolution** — `copa evolve` finds your most-used commands from zsh history and promotes them
- **Groups** — organize commands by project, device, or workflow
- **Sharing** — export/import command sets as `.copa` JSON files for team sharing
- **MCP server** — expose your commands to Claude Code (or any MCP client)
- **Zero latency** — precmd hook records usage in the background

## Install

```bash
# Requirements: Python 3.12+, fzf
brew install fzf  # if not already installed

pip install copa
# or from source:
git clone https://github.com/markstanford/copa.git
cd copa
pip install -e .
```

Add shell integration to your `.zshrc`:

```bash
source /path/to/copa/copa.zsh
```

Initialize the database:

```bash
copa _init
```

## Quick Start

```bash
# Import your shell history
copa sync

# Add a command manually
copa add "adb shell cmd bluetooth_manager enable" -d "Enable Bluetooth" -g bluetooth

# List top commands by score
copa list

# Search by keyword
copa search bluetooth

# Auto-promote frequent commands from history
copa evolve -k 20

# Add descriptions to undescribed commands
copa fix

# Scan ~/bin/ scripts
copa scan

# Open fzf command palette (or press Ctrl+R)
copa fzf-list --mode all | fzf
```

## Sharing

Export a group as a `.copa` file:

```bash
copa share export bluetooth -o bluetooth.copa
```

Share it with your team (via git, fbsource, or any file share):

```bash
copa share load bluetooth.copa
copa share load /path/to/team/commands.copa
copa share sync /path/to/team/copa-files/
```

`.copa` file format:

```json
{
    "copa_version": "1.0",
    "name": "bluetooth",
    "description": "Bluetooth commands for Android devices",
    "author": "markstanford",
    "commands": [
        {
            "command": "adb shell cmd bluetooth_manager enable",
            "description": "Enable Bluetooth",
            "tags": ["bt", "android"]
        }
    ]
}
```

## MCP Server (Claude Code integration)

Copa includes an MCP server so Claude Code can search and add commands.

Install the MCP dependency:

```bash
pip install copa[mcp]
```

Add to your Claude Code MCP config (`.mcp.json` in your project or home dir):

```json
{
    "mcpServers": {
        "copa": {
            "command": "python3",
            "args": ["-m", "copa.mcp_server"]
        }
    }
}
```

Available MCP tools:
- `copa_search` — search commands by keyword
- `copa_list_commands` — list commands ranked by score
- `copa_list_groups` — list all groups
- `copa_get_stats` — usage statistics
- `copa_add_command` — add a command
- `copa_update_description` — update a description
- `copa_create_group` — create a group with commands
- `copa_bulk_add` — bulk add commands

## CLI Reference

| Command | Purpose |
|---------|---------|
| `copa add "cmd" -d "desc" -g group` | Save a command |
| `copa list [-g group] [-n limit]` | List by score |
| `copa search "query"` | FTS search |
| `copa remove ID` | Remove a command |
| `copa stats` | Usage statistics |
| `copa sync` | Import from zsh history |
| `copa scan [--dir ~/bin]` | Import script metadata |
| `copa evolve [-k 20]` | Auto-add frequent commands |
| `copa fix` | Add missing descriptions |
| `copa share export GROUP -o file` | Export group |
| `copa share load SOURCE` | Load shared set |
| `copa share list` | List shared sets |
| `copa share sync DIR` | Sync .copa files from dir |

## How Scoring Works

```
score = 2.0 * log(1 + frequency) + 5.0 * 0.5^(age_seconds / 7_days)
```

Pinned commands get a +1000 bonus. This means a command used 10 times today scores higher than one used 100 times last month, which is usually what you want.

## License

MIT
