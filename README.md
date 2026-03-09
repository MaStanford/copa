# Copa — Command Palette for your shell

Copa tracks the commands you run, ranks them by frequency and recency, and gives you instant fuzzy search via fzf. Think of it as a smart, searchable, shareable upgrade to shell history.

## Features

- **Smart ranking** — commands scored by `2*log(1+freq) + 5*0.5^(age/7d)`, so frequent *and* recent commands float to the top
- **FTS search** — full-text search across commands and their descriptions
- **fzf integration** — Ctrl+R opens a fuzzy-searchable command palette with preview pane
- **Auto-evolution** — `copa evolve` finds your most-used commands from zsh history and promotes them
- **LLM descriptions** — `copa fix --auto` uses Claude or ollama to generate descriptions for undescribed commands
- **Script protocol** — `#@ Description:` / `#@ Usage:` headers in your scripts are auto-detected by `copa scan`
- **Groups** — organize commands by project, device, or workflow
- **Sharing** — export/import command sets as `.copa` JSON files for team sharing
- **Set filtering** — scope list, search, and fzf to a specific shared set with `--set`
- **MCP server** — expose your commands to Claude Code (or any MCP client)
- **Zero latency** — precmd hook records usage in the background

## Install

```bash
# Requirements: Python 3.12+, fzf
brew install fzf  # if not already installed

pip install copa
# or from source:
git clone https://github.com/MaStanford/copa.git
cd copa
pip install -e .

# Optional: ollama backend for LLM descriptions
pip install copa[ollama]
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

# Generate descriptions with LLM
copa fix --auto

# Scan ~/bin/ scripts
copa scan

# Open fzf command palette (or press Ctrl+R)
copa fzf-list --mode all | fzf
```

## LLM-Powered Descriptions

Copa can use an LLM to auto-generate descriptions for your undescribed commands. Two backends are supported:

### Configure

```bash
copa configure
```

This prompts you to choose a backend:

- **claude** (default) — shells out to the `claude` CLI. No API key needed if Claude Code is already authenticated.
- **ollama** — calls a local ollama server at `localhost:11434`. Copa checks that ollama is installed and running, prompts for a model name, and offers to pull it if missing.

Settings are stored in the Copa database (`meta` table).

### Bulk descriptions with `copa fix --auto`

```bash
# First, add undescribed commands
copa evolve -k 20

# Then generate descriptions with LLM suggestions
copa fix --auto
```

With `--auto`, each command gets an LLM-generated suggestion:

```
  [42] adb shell dumpsys bluetooth_manager
  Suggestion: Dump Bluetooth manager state
  Description [Dump Bluetooth manager state]:
```

- Press **Enter** to accept the suggestion
- **Type** a replacement to override it
- Press **q** to quit

Without `--auto`, `copa fix` behaves as before (blank prompt, Enter to skip).

### Single command description

```bash
copa describe 42
```

Generates a description for a specific command by ID. Same accept/edit flow as `fix --auto`.

## Script Metadata Protocol

Copa recognizes `#@` headers in script files (checked in the first 30 lines):

```bash
#!/bin/bash
#@ Description: Flash AOSP build to connected device
#@ Usage: flash_all.py <build-dir> -w [--skip firmware vendor_boot ...]
```

When scanned, this produces:

```
Flash AOSP build to connected device | Usage: flash_all.py <build-dir> -w [--skip firmware vendor_boot ...]
```

### Supported headers

| Header | Effect |
|--------|--------|
| `#@ Description: <text>` | Sets the command description (highest priority) |
| `#@ Usage: <text>` | Appended to description as `\| Usage: <text>` |

Scripts without `#@` headers still work — Copa falls back to legacy patterns (`# Description:`, `# Purpose:`, Python docstrings, generic comments).

### Scan scripts

```bash
copa scan               # scans ~/bin/ by default
copa scan --dir /path/to/scripts
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

### Filtering by shared set

Once you've loaded shared sets, you can scope commands to just that set:

```bash
# List only commands from the bluetooth shared set
copa list --set bluetooth

# Search within a shared set
copa search "enable" --set bluetooth

# fzf filtered to a shared set
copa fzf-list --mode set --set bluetooth | fzf
```

You can also filter by source type:

```bash
copa search "adb" --source shared
copa list --source scan
```

Create an alias for quick set-scoped search:

```bash
alias copa-bt='copa fzf-list --set bluetooth | fzf'
```

### `.copa` file format

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
| `copa list [-g group] [-s source] [--set name]` | List by score |
| `copa search "query" [-g group] [-s source] [--set name]` | FTS search |
| `copa remove ID` | Remove a command |
| `copa stats` | Usage statistics |
| `copa sync` | Import from zsh history |
| `copa scan [--dir ~/bin]` | Import script metadata |
| `copa evolve [-k 20]` | Auto-add frequent commands |
| `copa fix [--auto]` | Add missing descriptions (with optional LLM) |
| `copa describe ID` | Generate description for one command |
| `copa configure` | Set LLM backend (claude/ollama) |
| `copa share export GROUP -o file` | Export group |
| `copa share load SOURCE` | Load shared set |
| `copa share list` | List shared sets |
| `copa share sync DIR` | Sync .copa files from dir |
| `copa import FILE [-g group]` | Import commands from markdown |

## How Scoring Works

```
score = 2.0 * log(1 + frequency) + 5.0 * 0.5^(age_seconds / 7_days)
```

Pinned commands get a +1000 bonus. This means a command used 10 times today scores higher than one used 100 times last month, which is usually what you want.

## License

MIT
