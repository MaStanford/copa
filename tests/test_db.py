"""Tests for database flags support."""

import json
import pytest
from copa.db import Database


class TestDbFlags:
    """Test flags column, add_command, update_flags, and FTS."""

    def test_add_command_without_flags(self, tmp_db):
        cmd_id = tmp_db.add_command("echo hello", description="Say hello")
        cmd = tmp_db.get_command(cmd_id)
        assert cmd.flags == {}

    def test_add_command_with_flags(self, tmp_db):
        flags = {"--wipe": "Wipe userdata", "-v": "Verbose"}
        cmd_id = tmp_db.add_command("flash", description="Flash it", flags=flags)
        cmd = tmp_db.get_command(cmd_id)
        assert cmd.flags == flags

    def test_add_command_flags_none(self, tmp_db):
        cmd_id = tmp_db.add_command("test", flags=None)
        cmd = tmp_db.get_command(cmd_id)
        assert cmd.flags == {}

    def test_update_flags(self, tmp_db):
        cmd_id = tmp_db.add_command("flash", description="Flash it")
        assert tmp_db.get_command(cmd_id).flags == {}

        flags = {"--wipe": "Wipe userdata"}
        tmp_db.update_flags(cmd_id, flags)
        cmd = tmp_db.get_command(cmd_id)
        assert cmd.flags == flags

    def test_update_flags_replaces(self, tmp_db):
        initial = {"--wipe": "Wipe"}
        cmd_id = tmp_db.add_command("flash", flags=initial)
        assert tmp_db.get_command(cmd_id).flags == initial

        updated = {"--wipe": "Wipe userdata", "-n": "Dry run"}
        tmp_db.update_flags(cmd_id, updated)
        assert tmp_db.get_command(cmd_id).flags == updated

    def test_flags_stored_as_json(self, tmp_db):
        flags = {"--wipe": "Wipe userdata"}
        cmd_id = tmp_db.add_command("flash", flags=flags)

        cur = tmp_db.conn.cursor()
        cur.execute("SELECT flags FROM commands WHERE id = ?", (cmd_id,))
        raw = cur.fetchone()["flags"]
        assert json.loads(raw) == flags

    def test_fts_search_finds_flag_description(self, tmp_db):
        tmp_db.add_command("flash_all", description="Flash build",
                           flags={"--wipe": "Wipe userdata before flashing"})
        results = tmp_db.search_commands("userdata")
        assert len(results) == 1
        assert results[0].command == "flash_all"

    def test_fts_search_finds_flag_name(self, tmp_db):
        tmp_db.add_command("deploy", description="Deploy app",
                           flags={"--verbose": "Enable verbose output"})
        results = tmp_db.search_commands("verbose")
        assert len(results) == 1
        assert results[0].command == "deploy"

    def test_fts_search_still_finds_description(self, tmp_db):
        tmp_db.add_command("adb shell cmd bluetooth_manager enable",
                           description="Enable Bluetooth on device")
        results = tmp_db.search_commands("bluetooth")
        assert len(results) >= 1
        assert any(r.command == "adb shell cmd bluetooth_manager enable" for r in results)

    def test_fts_search_still_finds_command_text(self, tmp_db):
        tmp_db.add_command("git push origin main")
        results = tmp_db.search_commands("push")
        assert len(results) == 1

    def test_migration_idempotent(self, tmp_path):
        """Calling init_db twice doesn't fail (migration is idempotent)."""
        db = Database(tmp_path / "test.db")
        db.init_db()
        db.add_command("test1", flags={"--foo": "bar"})
        db.init_db()  # second init should not fail
        cmd = db.search_commands("test1")
        assert len(cmd) == 1
        # FTS should still work after reinit
        results = db.search_commands("bar")
        assert len(results) == 1
        db.close()

    def test_flags_survive_duplicate_insert(self, tmp_db):
        """When adding a duplicate command in the same group, flags are preserved."""
        flags = {"--wipe": "Wipe it"}
        cmd_id = tmp_db.add_command("flash", description="Flash",
                                    group_name="test", flags=flags)
        # Add again to same group (triggers UPDATE path)
        cmd_id2 = tmp_db.add_command("flash", description="",
                                     group_name="test")
        assert cmd_id == cmd_id2
        cmd = tmp_db.get_command(cmd_id)
        assert cmd.flags == flags
        assert cmd.frequency == 2
