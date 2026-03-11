"""Tests for modal group commands and config changes."""

from click.testing import CliRunner

from copa.cli import cli
from copa.config import DEFAULT_KEYS, LABELS, emit_zsh_config, load_config
from copa.db import Database


class TestListGroupsForAssign:
    """Test the _list-groups-for-assign hidden command."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_internal

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_internal, "get_db", lambda: db)
        return db

    def test_outputs_none_first(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["_list-groups-for-assign"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        # Delimited format: 0┃(none)┃
        assert "(none)" in lines[0]
        assert "┃" in lines[0]

    def test_outputs_groups(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        db.add_command("cmd1", group_name="alpha")
        db.add_command("cmd2", group_name="beta")
        runner = CliRunner()
        result = runner.invoke(cli, ["_list-groups-for-assign"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert "(none)" in lines[0]
        group_names = [line.split("┃")[1] for line in lines]
        assert "alpha" in group_names
        assert "beta" in group_names

    def test_no_groups_just_none(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["_list-groups-for-assign"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        assert "(none)" in lines[0]


class TestSetGroupDirect:
    """Test the _set-group-direct hidden command."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_internal

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_internal, "get_db", lambda: db)
        return db

    def test_assigns_group(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        result = runner.invoke(cli, ["_set-group-direct", str(cmd_id), "mygroup"])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert cmd.group_name == "mygroup"

    def test_clears_group_with_none(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello", group_name="old")
        runner = CliRunner()
        result = runner.invoke(cli, ["_set-group-direct", str(cmd_id), "(none)"])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert cmd.group_name is None

    def test_no_group_arg_clears(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello", group_name="old")
        runner = CliRunner()
        result = runner.invoke(cli, ["_set-group-direct", str(cmd_id)])
        assert result.exit_code == 0
        cmd = db.get_command(cmd_id)
        assert cmd.group_name is None


class TestConfigToggleHeader:
    """Test toggle_header key in config."""

    def test_toggle_header_in_defaults(self):
        assert "toggle_header" in DEFAULT_KEYS
        assert DEFAULT_KEYS["toggle_header"] == "ctrl-h"

    def test_toggle_header_label(self):
        assert "toggle_header" in LABELS
        assert LABELS["toggle_header"] == "keys"

    def test_load_config_includes_toggle_header(self):
        config = load_config()
        assert config["toggle_header"] == "ctrl-h"

    def test_emit_zsh_config_has_toggle_header_key(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_TOGGLE_HEADER_KEY='ctrl-h'" in output

    def test_header_is_two_lines(self):
        config = load_config()
        output = emit_zsh_config(config)
        # Find the _COPA_HEADER line
        for line in output.split("\n"):
            if line.startswith("_COPA_HEADER="):
                # Should contain \\n for the 2-line split
                assert "\\n" in line
                break
        else:
            raise AssertionError("_COPA_HEADER not found in output")

    def test_header_row1_has_keys_label(self):
        config = load_config()
        output = emit_zsh_config(config)
        for line in output.split("\n"):
            if line.startswith("_COPA_HEADER="):
                assert "^H:keys" in line
                break

    def test_header_row2_has_action_keys(self):
        config = load_config()
        output = emit_zsh_config(config)
        for line in output.split("\n"):
            if line.startswith("_COPA_HEADER="):
                # After the \n split, second row should have these
                assert "^G:grp" in line
                assert "^D:desc" in line
                assert "^F:flag" in line
                assert "^S:scope" in line
                break


class TestTtyHelpersInCommon:
    """Test that tty helpers are accessible from cli_common."""

    def test_open_tty_importable(self):
        from copa.cli_common import _open_tty

        assert callable(_open_tty)

    def test_close_tty_importable(self):
        from copa.cli_common import _close_tty

        assert callable(_close_tty)

    def test_close_tty_noop_on_none(self):
        from copa.cli_common import _close_tty

        # Should not raise
        _close_tty(None, None)

    def test_cli_internal_imports_from_common(self):
        """cli_internal should import tty helpers from cli_common."""
        import copa.cli_internal

        assert copa.cli_internal._open_tty is not None
        assert copa.cli_internal._close_tty is not None

    def test_cli_llm_imports_from_common(self):
        """cli_llm should import tty helpers from cli_common."""
        import copa.cli_llm

        assert copa.cli_llm._open_tty is not None
        assert copa.cli_llm._close_tty is not None
