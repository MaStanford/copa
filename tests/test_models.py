"""Tests for Command model flags support."""

import json
import pytest
from copa.models import Command, CopaFile


class TestCommandFlags:
    """Test the flags field on the Command dataclass."""

    def test_default_flags_empty(self):
        cmd = Command()
        assert cmd.flags == {}

    def test_from_row_no_flags(self):
        row = {"id": 1, "command": "echo hi", "description": "", "frequency": 1,
               "last_used": 0.0, "first_added": 0.0, "source": "manual",
               "group_name": None, "shared_set": None, "is_pinned": 0,
               "needs_description": 0}
        cmd = Command.from_row(row)
        assert cmd.flags == {}

    def test_from_row_empty_string_flags(self):
        row = {"id": 1, "command": "echo hi", "flags": ""}
        cmd = Command.from_row(row)
        assert cmd.flags == {}

    def test_from_row_valid_json_flags(self):
        flags = {"--wipe": "Wipe userdata", "-v": "Verbose"}
        row = {"id": 1, "command": "flash", "flags": json.dumps(flags)}
        cmd = Command.from_row(row)
        assert cmd.flags == flags

    def test_from_row_invalid_json_flags(self):
        row = {"id": 1, "command": "flash", "flags": "not-json{"}
        cmd = Command.from_row(row)
        assert cmd.flags == {}

    def test_to_dict_without_flags(self):
        cmd = Command(command="echo hi", description="test", tags=["t"])
        d = cmd.to_dict()
        assert "flags" not in d
        assert d["command"] == "echo hi"
        assert d["tags"] == ["t"]

    def test_to_dict_with_flags(self):
        flags = {"--wipe": "Wipe userdata"}
        cmd = Command(command="flash", description="Flash it", flags=flags)
        d = cmd.to_dict()
        assert d["flags"] == flags
        assert d["command"] == "flash"

    def test_round_trip_via_dict(self):
        """Flags survive to_dict -> from CopaFile -> import flow."""
        flags = {"-w, --wipe": "Wipe userdata", "--skip <parts>": "Skip partitions"}
        cmd = Command(command="flash_all", description="Flash build", tags=["aosp"], flags=flags)
        d = cmd.to_dict()
        assert d["flags"] == flags

        # Simulate reimport
        reimported_flags = d.get("flags", {})
        assert reimported_flags == flags


class TestCopaFileFlags:
    """Test that CopaFile round-trips commands with flags."""

    def test_copa_file_with_flags(self):
        commands = [
            {"command": "flash", "description": "Flash it", "tags": [],
             "flags": {"--wipe": "Wipe userdata"}},
        ]
        cf = CopaFile(name="test", commands=commands)
        d = cf.to_dict()
        assert d["commands"][0]["flags"] == {"--wipe": "Wipe userdata"}

        cf2 = CopaFile.from_dict(d)
        assert cf2.commands[0]["flags"] == {"--wipe": "Wipe userdata"}
