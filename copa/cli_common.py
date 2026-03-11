"""Shared utilities for Copa CLI modules."""

from __future__ import annotations

from click.shell_completion import CompletionItem

from .db import Database


def get_db() -> Database:
    db = Database()
    db.init_db()
    return db


# --- TTY helpers for fzf execute() bindings ---


def _open_tty():
    """Open /dev/tty with echo enabled for use inside fzf execute() bindings.

    fzf disables terminal echo before launching execute() subcommands.
    We re-enable it so users can see what they type.

    Returns (tty_file, original_termios) or (None, None) on failure.
    """
    try:
        tty = open("/dev/tty", "r+")
    except OSError:
        return None, None

    old_attrs = None
    try:
        import termios

        fd = tty.fileno()
        old_attrs = termios.tcgetattr(fd)
        new_attrs = termios.tcgetattr(fd)
        # Enable echo (ECHO) and canonical mode (ICANON) for line-buffered input
        new_attrs[3] |= termios.ECHO | termios.ICANON
        termios.tcsetattr(fd, termios.TCSANOW, new_attrs)
    except (ImportError, termios.error):
        pass  # termios not available (non-Unix) — proceed without echo fix

    return tty, old_attrs


def _close_tty(tty, old_attrs):
    """Restore terminal attributes and close the tty file."""
    if tty is None:
        return
    if old_attrs is not None:
        try:
            import termios

            termios.tcsetattr(tty.fileno(), termios.TCSANOW, old_attrs)
        except (ImportError, termios.error):
            pass
    tty.close()


# --- Shell completion helpers ---


def complete_group(ctx, param, incomplete):
    """Complete group names from the database."""
    try:
        db = get_db()
        return [CompletionItem(g) for g in db.get_groups() if g.startswith(incomplete)]
    except Exception:
        return []


def complete_shared_set(ctx, param, incomplete):
    """Complete shared set names from the database."""
    try:
        db = get_db()
        return [CompletionItem(s.name) for s in db.get_shared_sets() if s.name.startswith(incomplete)]
    except Exception:
        return []


def complete_source(ctx, param, incomplete):
    """Complete source values from the database."""
    try:
        db = get_db()
        return [CompletionItem(s) for s in db.get_sources() if s.startswith(incomplete)]
    except Exception:
        return []
