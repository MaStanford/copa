"""Keybinding configuration for Copa's fzf command composition."""

from __future__ import annotations

import re
from pathlib import Path

# Action name -> default fzf key
DEFAULT_KEYS: dict[str, str] = {
    "compose": "ctrl-x",
    "describe": "ctrl-d",
    "group": "ctrl-g",
    "flags": "ctrl-f",
    "filter_group": "ctrl-s",
    "cycle_group": "ctrl-n",
    "toggle_header": "ctrl-h",
    "select": "ctrl-b",
}

# Composition operators available in the compose submenu
# Order determines numbering in the menu
COMPOSE_OPERATORS: list[tuple[str, str, str]] = [
    # (label, suffix, behavior: "continue" or "close")
    ("|", " | ", "continue"),
    ("&&", " && ", "continue"),
    (">", " > ", "continue"),
    ("&", " &", "close"),
    ("2>&1", " 2>&1", "close"),
    ("2>/dev/null", " 2>/dev/null", "close"),
]

# Action name -> shell suffix appended to the command (kept for backwards compat)
SUFFIXES: dict[str, str] = {
    "pipe": " | ",
    "chain": " && ",
    "redirect": " > ",
    "background": " &",
    "merge_output": " 2>&1",
    "suppress": " 2>/dev/null",
}

# Composition actions that re-open fzf (continue) vs close it
DEFAULT_CONTINUE: set[str] = {"pipe", "chain", "redirect"}

# Action name -> short label for the header
LABELS: dict[str, str] = {
    "compose": "compose",
    "group": "grp",
    "describe": "desc",
    "flags": "flag",
    "filter_group": "scope",
    "cycle_group": "↻grp",
    "toggle_header": "keys",
    "select": "sel",
}

# Keys that cannot be overridden by user config
RESERVED_KEYS = {"ctrl-r", "enter"}

# Valid fzf key pattern: ctrl-<letter>, ctrl-/, alt-<letter>, etc.
_VALID_KEY_RE = re.compile(r"^(ctrl|alt)-[a-z/]$")


def _format_key_label(fzf_key: str) -> str:
    """Convert fzf key name to compact header label: ctrl-g -> ^G, ctrl-/ -> ^/."""
    if fzf_key.startswith("ctrl-"):
        char = fzf_key[5:]
        return f"^{char.upper()}"
    if fzf_key.startswith("alt-"):
        char = fzf_key[4:]
        return f"M-{char.upper()}"
    return fzf_key


def load_config(path: Path | None = None) -> dict:
    """Load keybinding and feature config from TOML, merged with defaults.

    Returns a dict with:
    - All action_name -> fzf_key entries (keybindings)
    - "_completion_branding" -> bool (whether to show Copa branding on tab completions)
    - "_completion_mode" -> str (fallback|always|hybrid|never)

    Silently ignores: unknown actions, invalid key names, reserved keys,
    duplicate assignments. Falls back to all defaults on malformed TOML.
    """
    config: dict = dict(DEFAULT_KEYS)
    config["_completion_branding"] = True  # default: show branding
    config["_completion_mode"] = "hybrid"  # default: Copa + native completions shown together
    # _continue_actions kept for backwards compat with old config files
    config["_continue_actions"] = set(DEFAULT_CONTINUE)
    config["_suggest_enabled"] = True  # default: inline suggestions on
    config["_suggest_min_length"] = 2  # minimum chars before querying
    config["_suggest_tab_accept"] = 2  # 1=direct accept, 2=open menu first
    config["_suggest_color"] = "242"  # ghost text color (256-color palette)
    config["_suggest_directory_aware"] = True  # boost suggestions from same directory

    if path is None:
        path = Path.home() / ".copa" / "config.toml"

    if not path.is_file():
        return config

    try:
        import tomllib

        data = tomllib.loads(path.read_text())
    except Exception:
        return config

    # [completion] section
    completion_section = data.get("completion")
    if isinstance(completion_section, dict):
        branding = completion_section.get("branding")
        if isinstance(branding, bool):
            config["_completion_branding"] = branding
        mode = completion_section.get("mode")
        if isinstance(mode, str) and mode in ("fallback", "always", "hybrid", "never"):
            config["_completion_mode"] = mode

    # [layout] section — fzf height and preview pane size
    layout_section = data.get("layout")
    if isinstance(layout_section, dict):
        height = layout_section.get("height")
        if isinstance(height, (int, str)):
            config["_height"] = str(height)
        preview = layout_section.get("preview_size")
        if isinstance(preview, (int, str)):
            config["_preview_size"] = str(preview)

    # [composition] section — which actions re-open fzf vs close it
    composition_section = data.get("composition")
    if isinstance(composition_section, dict):
        continue_list = composition_section.get("continue")
        if isinstance(continue_list, list):
            # Only keep valid composition action names (those that have suffixes)
            config["_continue_actions"] = {name for name in continue_list if isinstance(name, str) and name in SUFFIXES}

    # [suggest] section — inline suggestion settings
    suggest_section = data.get("suggest")
    if isinstance(suggest_section, dict):
        enabled = suggest_section.get("enabled")
        if isinstance(enabled, bool):
            config["_suggest_enabled"] = enabled
        min_length = suggest_section.get("min_length")
        if isinstance(min_length, int) and min_length >= 1:
            config["_suggest_min_length"] = min_length
        tab_accept = suggest_section.get("tab_accept")
        if isinstance(tab_accept, int) and tab_accept in (1, 2):
            config["_suggest_tab_accept"] = tab_accept
        color = suggest_section.get("color")
        if isinstance(color, (int, str)):
            config["_suggest_color"] = str(color)
        directory_aware = suggest_section.get("directory_aware")
        if isinstance(directory_aware, bool):
            config["_suggest_directory_aware"] = directory_aware

    keys_section = data.get("keys")
    if not isinstance(keys_section, dict):
        return config

    # Track which fzf keys are already assigned (from defaults not yet overridden)
    used_keys = {v for k, v in config.items() if not k.startswith("_")}

    for action, key in keys_section.items():
        # Skip unknown actions
        if action not in DEFAULT_KEYS:
            continue
        # Validate key format
        if not isinstance(key, str) or not _VALID_KEY_RE.match(key):
            continue
        # Skip reserved keys
        if key in RESERVED_KEYS:
            continue
        # Skip duplicate assignments (another action already has this key)
        # But allow if this action's default already uses this key
        if key in used_keys and config[action] != key:
            continue

        # Remove old key from used set, assign new one
        old_key = config[action]
        used_keys.discard(old_key)
        config[action] = key
        used_keys.add(key)

    return config


def emit_zsh_config(config: dict[str, str]) -> str:
    """Generate zsh variable assignments for the fzf widget.

    Output is eval'd by copa.zsh at shell startup.
    """
    lines: list[str] = []

    # Action keys
    describe_key = config.get("describe", DEFAULT_KEYS["describe"])
    group_key = config.get("group", DEFAULT_KEYS["group"])
    flags_key = config.get("flags", DEFAULT_KEYS["flags"])
    filter_group_key = config.get("filter_group", DEFAULT_KEYS["filter_group"])
    cycle_group_key = config.get("cycle_group", DEFAULT_KEYS["cycle_group"])
    toggle_header_key = config.get("toggle_header", DEFAULT_KEYS["toggle_header"])
    compose_key = config.get("compose", DEFAULT_KEYS["compose"])
    select_key = config.get("select", DEFAULT_KEYS["select"])

    # No more --expect keys — compose menu handles operators via execute
    lines.append("_COPA_EXPECT=''")
    lines.append(f"_COPA_DESCRIBE_KEY='{describe_key}'")
    lines.append(f"_COPA_GROUP_KEY='{group_key}'")
    lines.append(f"_COPA_FLAGS_KEY='{flags_key}'")
    lines.append(f"_COPA_FILTER_GROUP_KEY='{filter_group_key}'")
    lines.append(f"_COPA_CYCLE_GROUP_KEY='{cycle_group_key}'")
    lines.append(f"_COPA_TOGGLE_HEADER_KEY='{toggle_header_key}'")
    lines.append(f"_COPA_COMPOSE_KEY='{compose_key}'")
    lines.append(f"_COPA_SELECT_KEY='{select_key}'")

    # Build header as a single line; copa.zsh wraps it based on terminal width
    parts = ["Copa", f"{_format_key_label('ctrl-r')}:cycle"]
    for action in ("compose", "group", "describe", "flags", "filter_group", "cycle_group", "select", "toggle_header"):
        key = config.get(action, DEFAULT_KEYS[action])
        label = LABELS[action]
        parts.append(f"{_format_key_label(key)}:{label}")
    header = " | ".join(parts)
    lines.append(f"_COPA_HEADER='{header}'")

    # Layout config
    height = config.get("_height", "80%")
    lines.append(f"_COPA_HEIGHT='{height}'")
    preview_size = config.get("_preview_size", "40%")
    lines.append(f"_COPA_PREVIEW_SIZE='{preview_size}'")

    # Completion config
    branding = config.get("_completion_branding", True)
    lines.append(f"_COPA_COMPLETION_BRANDING='{'true' if branding else 'false'}'")
    completion_mode = config.get("_completion_mode", "fallback")
    lines.append(f"_COPA_COMPLETION_MODE='{completion_mode}'")

    # Inline suggestion config
    suggest_enabled = config.get("_suggest_enabled", True)
    lines.append(f"_COPA_SUGGEST_ENABLED='{'true' if suggest_enabled else 'false'}'")
    lines.append(f"_COPA_SUGGEST_MIN_LENGTH='{config.get('_suggest_min_length', 2)}'")
    lines.append(f"_COPA_SUGGEST_TAB_ACCEPT='{config.get('_suggest_tab_accept', 2)}'")
    lines.append(f"_COPA_SUGGEST_COLOR='{config.get('_suggest_color', '242')}'")
    suggest_dir = config.get("_suggest_directory_aware", True)
    lines.append(f"_COPA_SUGGEST_DIR_AWARE='{'true' if suggest_dir else 'false'}'")

    return "\n".join(lines)
