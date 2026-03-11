# Copa — Command Palette for your shell

[![CI](https://github.com/MaStanford/copa/actions/workflows/ci.yml/badge.svg)](https://github.com/MaStanford/copa/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/copa-cli)](https://pypi.org/project/copa-cli/)
[![Python](https://img.shields.io/pypi/pyversions/copa-cli)](https://pypi.org/project/copa-cli/)

Copa tracks the commands you run, ranks them by frequency and recency, and gives you instant fuzzy search via fzf. Think of it as a smart, searchable, shareable upgrade to shell history.

## Features

- **Smart ranking** — commands scored by `2*log(1+freq) + 8*0.5^(age/3d)`, so frequent *and* recent commands float to the top
- **FTS search** — full-text search across commands and their descriptions
- **fzf integration** — Ctrl+R opens a fuzzy-searchable command palette with preview pane; searches across commands *and* their descriptions
- **Tab completion** — Copa supplements zsh's tab completion for *any* command using your command history database
- **Auto-evolution** — `copa evolve` finds your most-used commands from zsh history and promotes them
- **LLM descriptions** — `copa fix --auto` uses Claude or ollama to generate descriptions for undescribed commands
- **Script protocol** — `#@ Description:` / `#@ Usage:` / `#@ Purpose:` / `#@ Flag:` headers in your scripts are auto-detected by `copa scan` across all `$PATH` directories
- **Flag documentation** — document command flags with descriptions; flags are searchable, visible in the preview pane, and preserved in `.copa` exports
- **Groups & Ctrl+G** — organize commands by project, device, or workflow; assign groups inline from the fzf palette with Ctrl+G
- **Sharing & `copa create`** — export/import command sets as `.copa` JSON files; `copa create` scaffolds a `.copa` file from an existing group
- **Set filtering** — scope list, search, and fzf to a specific shared set with `--set`
- **MCP server** — expose your commands to Claude Code (or any MCP client)
- **Zero latency** — precmd hook records usage in the background

## Install

### Prerequisites

- **Python 3.12+**
- **fzf** — required for Ctrl+R command palette

```bash
# macOS
brew install fzf

# Linux (apt)
sudo apt install fzf

# or see https://github.com/junegunn/fzf#installation
```

### Install Copa

```bash
pip install copa-cli
# or from source:
git clone https://github.com/MaStanford/copa.git
cd copa
pip install -e .

# Optional: ollama backend for LLM descriptions
pip install copa-cli[ollama]
```

### Shell integration (required)

Add this line to your `~/.zshrc`:

```bash
eval "$(copa init zsh)"
```

Then restart your shell or run `source ~/.zshrc`. This does three things:

1. **Records every command you run** — a `precmd` hook silently calls `copa _record` in the background after each command, building up frequency and recency data with zero latency impact.
2. **Replaces Ctrl+R** — the default zsh reverse-history-search is replaced with Copa's fzf-powered command palette (see below).
3. **Supplements tab completion** — Copa registers as a completer so that any command gets completion candidates from your Copa database. The behavior is configurable (`fallback`, `hybrid`, `always`, or `never`) — see [Tab Completion](#tab-completion).

Initialize the database:

```bash
copa _init
```

## Ctrl+R — fzf Command Palette

Once shell integration is sourced, pressing **Ctrl+R** opens an fzf-powered command palette instead of the default zsh reverse search. This is Copa's primary interface.

### What you see

Copa pipes every tracked command into fzf with aligned columns:

```
 command text (padded)  ┃  [group]  freq×N
```

The left panel shows the command text. The right panel shows metadata: a pin indicator, group badge (dim magenta), and frequency count (dim). Descriptions and flag documentation are not shown in the list — they appear in the preview pane but are still included as a hidden field that fzf searches. This means typing "bluetooth" in fzf will find a command whose description mentions "bluetooth" even if the command text doesn't contain it.

**fzf searches across all fields** — the command text, group names, descriptions, and flag documentation. A hidden search field contains the full description and flag text so fzf's fuzzy matching covers everything even though only the command and metadata columns are displayed.

This is the key difference from plain zsh Ctrl+R: you're not just searching raw history text, you're searching annotated, described, ranked commands.

### Modes

The header shows available modes. Press **Ctrl+R** again while fzf is open to cycle:

| Mode | Sort order | Use case |
|------|-----------|----------|
| `all` | Score (frequency + recency) | Default — best commands float to top |
| `frequent` | Frequency only | Find your most-used commands |
| `recent` | Last used time | Find commands you ran recently |

### Keybindings

While the fzf palette is open, these keys are available:

| Key | Action | Effect |
|-----|--------|--------|
| **Ctrl+R** | Cycle mode | all → frequent → recent → all |
| **Ctrl+V** | Append `&` | Run selected command in background |
| **Ctrl+O** | Append `2>&1` | Merge stderr into stdout |
| **Ctrl+X** | Append `\|` | Pipe into next command |
| **Ctrl+T** | Append `>` | Redirect output |
| **Ctrl+A** | Append `&&` | Chain with next command |
| **Ctrl+/** | Append `2>/dev/null` | Suppress stderr |
| **Ctrl+S** | Scope by group | Opens inline group list — Enter filters to that group, ESC returns to all |
| **Ctrl+G** | Assign group | Opens inline group list — Enter assigns the group to the highlighted command |
| **Ctrl+N** | Cycle group | Cycles through groups: (all) → group1 → group2 → ... → (all) |
| **Ctrl+D** | Describe | Generate/edit a description using LLM (with tty-aware input) |
| **Ctrl+F** | Edit flags | Add flag documentation to the highlighted command |
| **Ctrl+H** | Toggle header | Show/hide the key hints for more screen space |
| **ESC** | Cancel/back | In scope/group mode: returns to command list. Otherwise: closes fzf |

Keybindings are configurable via `~/.copa/config.toml`. See [Configuration](#configuration).

### Preview pane

The right side shows a detail card for the highlighted command: full description, usage, purpose, flag documentation, score breakdown, frequency, last used, source, group, shared set, and tags.

### Result

Selecting a command places it directly into your shell prompt (without executing it), so you can review or edit before pressing Enter.

## Tab Completion

Copa supplements zsh's built-in tab completion for **any** command — not just Copa's own CLI. Once `copa.zsh` is sourced, Copa registers as a completer in zsh's completion system.

### Completion modes

Copa supports four completion modes, configured via `~/.copa/config.toml`:

| Mode | Behavior |
|------|----------|
| `fallback` | **(default)** Only show Copa completions when native completers found nothing |
| `hybrid` | Show Copa completions alongside native completions (in a separate group) |
| `always` | Copa completions replace native completions |
| `never` | Disable Copa tab completion entirely |

```toml
# ~/.copa/config.toml
[completion]
mode = "fallback"    # fallback | hybrid | always | never
branding = true      # show "Copa history" group header
```

### How it works

When you press Tab, Copa queries its database for commands matching what you've typed so far and suggests the next word(s):

```
$ adb shell dump<TAB>
→ dumpsys  dumpstate
```

Copa looks at your tracked commands starting with `adb shell dump` and extracts the next word from each match. Candidates are deduplicated and ordered by frequency.

### Examples

```bash
# Complete subcommands for adb
adb <TAB>
→ shell  devices  logcat  push  pull  ...

# Complete arguments deeper in the command
adb shell cmd bluetooth_manager <TAB>
→ enable  disable  ...
```

This works automatically once `copa.zsh` is sourced — no extra setup needed. The more commands you use (and track with Copa), the better the completions get.

Copa's own CLI completions (`copa li<TAB>` → `list`) continue to work as before via Click's built-in completion.

## Quick Start

```bash
# Import your shell history
copa sync

# Add a command manually
copa add "adb shell cmd bluetooth_manager enable" -d "Enable Bluetooth" -g bluetooth

# Add a command with flag documentation
copa add "flash_all" -d "Flash AOSP build" -f "--wipe: Wipe userdata" -f "-v: Verbose"

# Create a .copa file from a group (or scaffold an empty one)
copa create -g bluetooth

# List top commands by score
copa list

# Search by keyword
copa search bluetooth

# Auto-promote frequent commands from history
copa evolve -k 20

# Auto-promote and generate descriptions in one pass
copa evolve -k 20 --auto

# Generate descriptions with LLM
copa fix --auto

# Scan $PATH for scripts with metadata
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

# Or do both in one step
copa evolve -k 20 --auto
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

Copa recognizes `#@` headers in script files (checked in the first 50 lines):

```bash
#!/bin/bash
#@ Description: Flash AOSP build to connected device
#@ Usage: flash_all.py <build-dir> -w [--skip firmware vendor_boot ...]
#@ Purpose: Streamline the device flashing workflow
#@ Flag: -w, --wipe: Wipe userdata before flashing
#@ Flag: --skip <parts>: Skip specific partitions
#@ Flag: -n, --dry-run: Show what would be done without flashing
```

When scanned, Description, Usage, Purpose, and Flags are stored and displayed in the Ctrl+R preview pane:

```
Description: Flash AOSP build to connected device
Usage:       flash_all.py <build-dir> -w [--skip firmware vendor_boot ...]
Purpose:     Streamline the device flashing workflow

Flags:
  -w, --wipe           Wipe userdata before flashing
  --skip <parts>       Skip specific partitions
  -n, --dry-run        Show what would be done without flashing
```

### Supported headers

| Header | Effect |
|--------|--------|
| `#@ Description: <text>` | Sets the command description (highest priority) |
| `#@ Usage: <text>` | Usage / invocation syntax |
| `#@ Purpose: <text>` | Why the script exists / when to use it |
| `#@ Flag: <flag>: <description>` | Document a flag/option (repeatable) |

Scripts without `#@` headers still work — Copa falls back to legacy patterns (`# Description:`, `# Purpose:`, Python docstrings, generic comments).

### Scan scripts

```bash
copa scan               # scans all $PATH directories
copa scan --dir ~/bin   # scan a specific directory
```

## Sharing

Export a group as a `.copa` file:

```bash
# Using copa create (recommended — creates a .copa file you can edit)
copa create -g bluetooth

# Or using share export (direct export)
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
        },
        {
            "command": "flash_all",
            "description": "Flash AOSP build to device",
            "tags": ["aosp"],
            "flags": {
                "-w, --wipe": "Wipe userdata before flashing",
                "--skip <parts>": "Skip specific partitions"
            }
        }
    ]
}
```

## MCP Server (Claude Code integration)

Copa includes an MCP server so Claude Code can search and add commands.

Install the MCP dependency:

```bash
pip install copa-cli[mcp]
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

## Configuration

Copa is configured via `~/.copa/config.toml`. All settings are optional — Copa uses sensible defaults.

```toml
# ~/.copa/config.toml

# Keybindings for the Ctrl+R fzf palette
# Values are fzf key names: ctrl-<letter>, alt-<letter>, ctrl-/
# ctrl-r and enter are reserved and cannot be reassigned
[keys]
background = "ctrl-v"       # append &
merge_output = "ctrl-o"     # append 2>&1
pipe = "ctrl-x"             # append |
redirect = "ctrl-t"         # append >
chain = "ctrl-a"            # append &&
suppress = "ctrl-/"         # append 2>/dev/null
describe = "ctrl-d"         # LLM describe
group = "ctrl-g"            # assign group (inline modal)
flags = "ctrl-f"            # edit flags
filter_group = "ctrl-s"     # scope by group (inline modal)
cycle_group = "ctrl-n"      # cycle through groups
toggle_header = "ctrl-h"    # show/hide key hints

# Tab completion behavior
[completion]
mode = "fallback"           # fallback | hybrid | always | never
branding = true             # show "Copa history" group header
```

## CLI Reference

| Command | Purpose |
|---------|---------|
| `copa add "cmd" -d "desc" -g group -f "flag: desc"` | Save a command (with optional flags) |
| `copa create -g group [-o file]` | Create a .copa file from a group |
| `copa list [-g group] [-s source] [--set name]` | List by score |
| `copa search "query" [-g group] [-s source] [--set name]` | FTS search |
| `copa remove ID` | Remove a command |
| `copa stats` | Usage statistics |
| `copa sync` | Import from zsh history |
| `copa scan [--dir path]` | Import script metadata from $PATH |
| `copa evolve [-k 20] [--auto]` | Auto-add frequent commands (with optional LLM descriptions) |
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
score = 2.0 * log(1 + frequency) + 8.0 * 0.5^(age_seconds / 3_days)
```

Pinned commands get a +1000 bonus. The 3-day half-life means commands used in the last few days are strongly favored — a command used today scores ~8.0 recency, after 3 days ~4.0, after a week ~1.6.

## License

MIT
