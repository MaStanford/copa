"""Dataclasses for Copa entities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Command:
    """A tracked command."""

    id: int = 0
    command: str = ""
    description: str = ""
    frequency: int = 0
    last_used: float = 0.0
    first_added: float = 0.0
    source: str = "manual"  # history|manual|shared|scan|auto
    group_name: str | None = None
    shared_set: str | None = None
    is_pinned: bool = False
    needs_description: bool = False
    tags: list[str] = field(default_factory=list)
    flags: dict[str, str] = field(default_factory=dict)
    last_cwd: str = ""
    score: float = 0.0  # computed at query time

    @classmethod
    def from_row(cls, row: dict) -> Command:
        cmd = cls(
            id=row["id"],
            command=row["command"],
            description=row.get("description", ""),
            frequency=row.get("frequency", 0),
            last_used=row.get("last_used", 0.0),
            first_added=row.get("first_added", 0.0),
            source=row.get("source", "manual"),
            group_name=row.get("group_name"),
            shared_set=row.get("shared_set"),
            is_pinned=bool(row.get("is_pinned", 0)),
            needs_description=bool(row.get("needs_description", 0)),
        )
        flags_raw = row.get("flags", "")
        if flags_raw:
            try:
                cmd.flags = json.loads(flags_raw)
            except (json.JSONDecodeError, TypeError):
                cmd.flags = {}
        cmd.last_cwd = row.get("last_cwd", "")
        return cmd

    def to_dict(self) -> dict:
        d = {
            "command": self.command,
            "description": self.description,
            "tags": self.tags,
        }
        if self.flags:
            d["flags"] = self.flags
        return d


@dataclass
class SharedSet:
    """A shared command set."""

    name: str = ""
    description: str = ""
    source_path: str | None = None
    loaded_at: float = 0.0
    version: str = "1.0"
    author: str = ""

    @classmethod
    def from_row(cls, row: dict) -> SharedSet:
        return cls(
            name=row["name"],
            description=row.get("description", ""),
            source_path=row.get("source_path"),
            loaded_at=row.get("loaded_at", 0.0),
            version=row.get("version", "1.0"),
            author=row.get("author", ""),
        )


@dataclass
class RecipeStep:
    """A single step in a recipe."""

    id: int = 0
    recipe_id: int = 0
    step_order: int = 0
    command: str = ""
    description: str = ""

    @classmethod
    def from_row(cls, row: dict) -> RecipeStep:
        return cls(
            id=row.get("id", 0),
            recipe_id=row.get("recipe_id", 0),
            step_order=row.get("step_order", 0),
            command=row.get("command", ""),
            description=row.get("description", ""),
        )

    def to_dict(self) -> dict:
        d: dict = {"command": self.command}
        if self.description:
            d["description"] = self.description
        return d


@dataclass
class Recipe:
    """A multi-step command recipe."""

    id: int = 0
    name: str = ""
    description: str = ""
    group_name: str | None = None
    shared_set: str | None = None
    created_at: float = 0.0
    last_run: float = 0.0
    run_count: int = 0
    steps: list[RecipeStep] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict) -> Recipe:
        return cls(
            id=row.get("id", 0),
            name=row.get("name", ""),
            description=row.get("description", ""),
            group_name=row.get("group_name"),
            shared_set=row.get("shared_set"),
            created_at=row.get("created_at", 0.0),
            last_run=row.get("last_run", 0.0),
            run_count=row.get("run_count", 0),
        )

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.description:
            d["description"] = self.description
        return d


@dataclass
class CopaFile:
    """Represents a .copa export/import file."""

    copa_version: str = "1.0"
    name: str = ""
    description: str = ""
    author: str = ""
    commands: list[dict] = field(default_factory=list)
    recipes: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "copa_version": self.copa_version,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "commands": self.commands,
        }
        if self.recipes:
            d["recipes"] = self.recipes
        return d

    @classmethod
    def from_dict(cls, data: dict) -> CopaFile:
        return cls(
            copa_version=data.get("copa_version", "1.0"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            commands=data.get("commands", []),
            recipes=data.get("recipes", []),
        )
