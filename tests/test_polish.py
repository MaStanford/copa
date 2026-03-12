"""Tests for polish features: pin/unpin, edit, doctor, --json, first-run hint."""

import json

from click.testing import CliRunner

from copa.cli import cli
from copa.db import Database


class _DBMixin:
    """Shared DB setup for tests."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli as cli_mod
        import copa.cli_common

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(cli_mod, "get_db", lambda: db)
        return db


class TestPin(_DBMixin):
    """Test copa pin / unpin commands."""

    def test_pin_command(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["pin", str(cmd_id)])
        assert result.exit_code == 0
        assert "Pinned" in result.output
        cmd = db.get_command(cmd_id)
        assert cmd.is_pinned is True

    def test_unpin_command(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        db.pin_command(cmd_id, True)
        runner = CliRunner()
        result = runner.invoke(cli, ["unpin", str(cmd_id)])
        assert result.exit_code == 0
        assert "Unpinned" in result.output
        cmd = db.get_command(cmd_id)
        assert cmd.is_pinned is False

    def test_pin_nonexistent(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["pin", "9999"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestEdit(_DBMixin):
    """Test copa edit command."""

    def test_edit_description(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", str(cmd_id), "-d", "Say hello"])
        assert result.exit_code == 0
        assert "Updated" in result.output
        cmd = db.get_command(cmd_id)
        assert cmd.description == "Say hello"

    def test_edit_group(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", str(cmd_id), "-g", "greetings"])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert cmd.group_name == "greetings"

    def test_edit_clear_group(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello", group_name="old")
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", str(cmd_id), "-g", ""])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert cmd.group_name is None

    def test_edit_pin(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", str(cmd_id), "--pin"])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert cmd.is_pinned is True

    def test_edit_no_options(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", str(cmd_id)])
        assert result.exit_code == 0
        assert "nothing to change" in result.output

    def test_edit_nonexistent(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", "9999", "-d", "test"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_edit_flags(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("flash_all")
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", str(cmd_id), "-f", "--wipe: Wipe data", "-f", "-v: Verbose"])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert "--wipe" in cmd.flags
        assert cmd.flags["--wipe"] == "Wipe data"


class TestJsonOutput(_DBMixin):
    """Test --json flag on list and search."""

    def test_list_json(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        db.add_command("echo hello", description="Say hello")
        db.add_command("ls -la", description="List files")
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2
        assert all("command" in c for c in data)
        assert all("score" in c for c in data)

    def test_list_json_empty(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_search_json(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        db.add_command("echo hello", description="Say hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "hello", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["command"] == "echo hello"

    def test_search_json_empty(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "nonexistent", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []

    def test_list_json_includes_group(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        db.add_command("echo hello", group_name="greetings")
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json"])
        data = json.loads(result.output)
        assert data[0]["group"] == "greetings"

    def test_list_json_includes_pinned(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        db.pin_command(cmd_id, True)
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json"])
        data = json.loads(result.output)
        assert data[0]["pinned"] is True


class TestDoctor(_DBMixin):
    """Test copa doctor command."""

    def test_doctor_runs(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Copa Doctor" in result.output

    def test_doctor_checks_fzf(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert "fzf" in result.output


class TestFirstRunHint:
    """Test first-run hint in copa init zsh output."""

    def test_init_zsh_has_hint(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "zsh"])
        assert result.exit_code == 0
        assert "copa _init" in result.output
        assert "copa sync" in result.output
        assert "copa doctor" in result.output
