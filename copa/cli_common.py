"""Shared utilities for Copa CLI modules."""

from __future__ import annotations

from click.shell_completion import CompletionItem

from .db import Database


def get_db() -> Database:
    db = Database()
    db.init_db()
    return db


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
