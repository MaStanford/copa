"""Scoring algorithm: frequency + recency hybrid."""

from __future__ import annotations

import math
import time

from .models import Command

# Tuning constants
FREQ_WEIGHT = 2.0
RECENCY_WEIGHT = 5.0
HALF_LIFE_SECONDS = 7 * 24 * 3600  # 7 days
PIN_BONUS = 1000.0


def compute_score(cmd: Command, now: float | None = None) -> float:
    """Compute hybrid score: 2.0*log(1+freq) + 5.0*0.5^(age/7days).

    Pinned commands get +1000 bonus.
    """
    if now is None:
        now = time.time()

    freq_score = FREQ_WEIGHT * math.log(1 + cmd.frequency)

    age_seconds = max(0, now - cmd.last_used) if cmd.last_used > 0 else HALF_LIFE_SECONDS * 10
    recency_score = RECENCY_WEIGHT * (0.5 ** (age_seconds / HALF_LIFE_SECONDS))

    score = freq_score + recency_score

    if cmd.is_pinned:
        score += PIN_BONUS

    return score


def rank_commands(commands: list[Command], now: float | None = None) -> list[Command]:
    """Score and sort commands by descending score."""
    if now is None:
        now = time.time()
    for cmd in commands:
        cmd.score = compute_score(cmd, now)
    commands.sort(key=lambda c: c.score, reverse=True)
    return commands
