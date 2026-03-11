"""Tests for CLI add --flag and sharing flags round-trip."""

import json

from click.testing import CliRunner

from copa.cli import cli
from copa.db import Database
from copa.models import CopaFile
from copa.sharing import export_group, import_shared_set, load_copa_file


class TestCliAddFlags:
    """Test the copa add --flag option."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        # Patch get_db in every module that imports it
        import copa.cli
        import copa.cli_common

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli, "get_db", lambda: db)
        return db

    def test_add_with_single_flag(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "add",
                "flash_all",
                "-d",
                "Flash AOSP build",
                "-f",
                "--wipe: Wipe userdata",
            ],
        )
        assert result.exit_code == 0
        assert "Added" in result.output
        assert "flags: 1 documented" in result.output

        cmds = db.list_commands(limit=100)
        flash_cmds = [c for c in cmds if c.command == "flash_all"]
        assert len(flash_cmds) == 1
        assert flash_cmds[0].flags == {"--wipe": "Wipe userdata"}
        db.close()

    def test_add_with_multiple_flags(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "add",
                "deploy",
                "-f",
                "--verbose: Enable verbose output",
                "-f",
                "-n, --dry-run: Show what would happen",
            ],
        )
        assert result.exit_code == 0
        assert "flags: 2 documented" in result.output

        cmds = db.list_commands(limit=100)
        deploy_cmds = [c for c in cmds if c.command == "deploy"]
        assert len(deploy_cmds) == 1
        assert deploy_cmds[0].flags == {
            "--verbose": "Enable verbose output",
            "-n, --dry-run": "Show what would happen",
        }
        db.close()

    def test_add_without_flags(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(cli, ["add", "echo hello", "-d", "Say hello"])
        assert result.exit_code == 0
        assert "flags" not in result.output

        cmds = db.list_commands(limit=100)
        echo_cmds = [c for c in cmds if c.command == "echo hello"]
        assert len(echo_cmds) == 1
        assert echo_cmds[0].flags == {}
        db.close()

    def test_add_flag_without_description(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(cli, ["add", "cmd", "-f", "--verbose"])
        assert result.exit_code == 0

        cmds = db.list_commands(limit=100)
        cmd_cmds = [c for c in cmds if c.command == "cmd"]
        assert len(cmd_cmds) == 1
        assert cmd_cmds[0].flags == {"--verbose": ""}
        db.close()


class TestSharingFlags:
    """Test flags round-trip through .copa export/import."""

    def test_export_includes_flags(self, tmp_db):
        flags = {"--wipe": "Wipe userdata", "-v": "Verbose"}
        tmp_db.add_command("flash", description="Flash it", group_name="test-group", flags=flags)

        copa_file = export_group(tmp_db, "test-group")
        assert len(copa_file.commands) == 1
        assert copa_file.commands[0]["flags"] == flags

    def test_export_omits_empty_flags(self, tmp_db):
        tmp_db.add_command("echo hi", description="Say hello", group_name="test-group")
        copa_file = export_group(tmp_db, "test-group")
        assert "flags" not in copa_file.commands[0]

    def test_import_preserves_flags(self, tmp_db):
        copa_file = CopaFile(
            name="imported",
            commands=[
                {
                    "command": "flash_all",
                    "description": "Flash build",
                    "tags": ["aosp"],
                    "flags": {"--wipe": "Wipe userdata", "-n": "Dry run"},
                }
            ],
        )
        count = import_shared_set(tmp_db, copa_file, source_path="/tmp/test.copa")
        assert count == 1

        results = tmp_db.search_commands("flash_all")
        assert len(results) == 1
        assert results[0].flags == {"--wipe": "Wipe userdata", "-n": "Dry run"}

    def test_import_without_flags(self, tmp_db):
        copa_file = CopaFile(
            name="imported",
            commands=[
                {
                    "command": "echo hi",
                    "description": "Say hello",
                    "tags": [],
                }
            ],
        )
        count = import_shared_set(tmp_db, copa_file)
        assert count == 1
        results = tmp_db.search_commands("echo")
        assert results[0].flags == {}

    def test_export_import_round_trip(self, tmp_db, tmp_path):
        flags = {"-w, --wipe": "Wipe userdata", "--skip <parts>": "Skip partitions"}
        tmp_db.add_command("flash_all", description="Flash build", group_name="roundtrip", flags=flags, tags=["aosp"])

        # Export
        copa_file = export_group(tmp_db, "roundtrip", author="tester")
        file_path = tmp_path / "roundtrip.copa"
        file_path.write_text(json.dumps(copa_file.to_dict(), indent=2))

        # Import into a fresh db
        db2 = Database(tmp_path / "test2.db")
        db2.init_db()
        loaded = load_copa_file(file_path)
        count = import_shared_set(db2, loaded, source_path=str(file_path))
        assert count == 1

        results = db2.search_commands("flash_all")
        assert len(results) == 1
        assert results[0].flags == flags
        assert results[0].description == "Flash build"
        db2.close()
