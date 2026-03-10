"""Keybinding configuration for Copa's fzf command composition."""

from __future__ import annotations

import re
from pathlib import Path

# Action name -> default fzf key
DEFAULT_KEYS: dict[str, str] = {
    "background": "ctrl-v",
    "merge_output": "ctrl-o",
    "pipe": "ctrl-x",
    "redirect": "ctrl-t",
    "chain": "ctrl-a",
    "suppress": "ctrl-/",
    "describe": "ctrl-d",
    "group": "ctrl-g",
    "flags": "ctrl-f",
}

# Action name -> shell suffix appended to the command
SUFFIXES: dict[str, str] = {
    "background": " &",
    "merge_output": " 2>&1",
    "pipe": " | ",
    "redirect": " > ",
    "chain": " && ",
    "suppress": " 2>/dev/null",
}

# Action name -> short label for the header
LABELS: dict[str, str] = {
    "background": "&",
    "merge_output": "2>&1",
    "pipe": "|",
    "redirect": ">",
    "chain": "&&",
    "suppress": "quiet",
    "group": "grp",
    "describe": "desc",
    "flags": "flag",
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


def load_config(path: Path | None = None) -> dict[str, str]:
    """Load keybinding config from TOML, merged with defaults.

    Returns a dict of action_name -> fzf_key.
    Silently ignores: unknown actions, invalid key names, reserved keys,
    duplicate assignments. Falls back to all defaults on malformed TOML.
    """
    config = dict(DEFAULT_KEYS)

    if path is None:
        path = Path.home() / ".copa" / "config.toml"

    if not path.is_file():
        return config

    try:
        import tomllib

        data = tomllib.loads(path.read_text())
    except Exception:
        return config

    keys_section = data.get("keys")
    if not isinstance(keys_section, dict):
        return config

    # Track which fzf keys are already assigned (from defaults not yet overridden)
    used_keys = set(config.values())

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

    # Separate describe, group, and flags keys from expect keys (composition keys)
    describe_key = config.get("describe", DEFAULT_KEYS["describe"])
    group_key = config.get("group", DEFAULT_KEYS["group"])
    flags_key = config.get("flags", DEFAULT_KEYS["flags"])
    expect_keys = [
        config[action]
        for action in ("background", "merge_output", "pipe", "redirect", "chain", "suppress")
        if action in config
    ]

    lines.append(f"_COPA_EXPECT='{','.join(expect_keys)}'")
    lines.append(f"_COPA_DESCRIBE_KEY='{describe_key}'")
    lines.append(f"_COPA_GROUP_KEY='{group_key}'")
    lines.append(f"_COPA_FLAGS_KEY='{flags_key}'")

    # Build header: Copa | ^R:cycle | ^G:& | ^O:2>&1 | ...
    header_parts = ["Copa", f"{_format_key_label('ctrl-r')}:cycle"]
    for action in ("background", "merge_output", "pipe", "redirect", "chain", "suppress", "group", "describe", "flags"):
        key = config.get(action, DEFAULT_KEYS[action])
        label = LABELS[action]
        header_parts.append(f"{_format_key_label(key)}:{label}")
    header = " | ".join(header_parts)
    lines.append(f"_COPA_HEADER='{header}'")

    # Suffix associative array
    lines.append("typeset -gA _COPA_SUFFIXES")
    for action in ("background", "merge_output", "pipe", "redirect", "chain", "suppress"):
        key = config.get(action, DEFAULT_KEYS[action])
        suffix = SUFFIXES[action]
        lines.append(f"_COPA_SUFFIXES[{key}]='{suffix}'")

    return "\n".join(lines)
