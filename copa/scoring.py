"""Scoring algorithm: frequency + recency hybrid."""

from __future__ import annotations

import math
import time

from .models import Command

# Tuning constants
FREQ_WEIGHT = 2.0
RECENCY_WEIGHT = 8.0
HALF_LIFE_SECONDS = 3 * 24 * 3600  # 3 days
PIN_BONUS = 1000.0
DIR_EXACT_BONUS = 5.0  # bonus for commands last used in the same directory
DIR_PARENT_BONUS = 2.0  # bonus for commands used in a parent/child directory


def _dir_bonus(cmd_cwd: str, current_cwd: str) -> float:
    """Compute directory-proximity bonus."""
    if not cmd_cwd or not current_cwd:
        return 0.0
    if cmd_cwd == current_cwd:
        return DIR_EXACT_BONUS
    # Check parent/child relationship
    if current_cwd.startswith(cmd_cwd + "/") or cmd_cwd.startswith(current_cwd + "/"):
        return DIR_PARENT_BONUS
    return 0.0


def compute_score(
    cmd: Command,
    now: float | None = None,
    cwd: str | None = None,
    directory_aware: bool = True,
) -> float:
    """Compute hybrid score: 2.0*log(1+freq) + 8.0*0.5^(age/3days).

    Pinned commands get +1000 bonus.
    If directory_aware and cwd is set, commands used in the same directory get a boost.
    """
    if now is None:
        now = time.time()

    freq_score = FREQ_WEIGHT * math.log(1 + cmd.frequency)

    age_seconds = max(0, now - cmd.last_used) if cmd.last_used > 0 else HALF_LIFE_SECONDS * 10
    recency_score = RECENCY_WEIGHT * (0.5 ** (age_seconds / HALF_LIFE_SECONDS))

    score = freq_score + recency_score

    if cmd.is_pinned:
        score += PIN_BONUS

    if directory_aware and cwd:
        score += _dir_bonus(cmd.last_cwd, cwd)

    return score


def rank_commands(
    commands: list[Command],
    now: float | None = None,
    cwd: str | None = None,
    directory_aware: bool = True,
) -> list[Command]:
    """Score and sort commands by descending score."""
    if now is None:
        now = time.time()
    for cmd in commands:
        cmd.score = compute_score(cmd, now, cwd=cwd, directory_aware=directory_aware)
    commands.sort(key=lambda c: c.score, reverse=True)
    return commands
