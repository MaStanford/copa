"""Tests for modal group commands, config changes, batch commands, describe prompt, and inline suggestions."""

import time
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from copa.cli import cli
from copa.config import DEFAULT_CONTINUE, DEFAULT_KEYS, LABELS, SUFFIXES, emit_zsh_config, load_config
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


class TestCompletionMode:
    """Test completion mode config."""

    def test_default_mode_is_hybrid(self):
        config = load_config()
        assert config["_completion_mode"] == "hybrid"

    def test_emit_zsh_config_has_completion_mode(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_COMPLETION_MODE='hybrid'" in output

    def test_load_config_accepts_valid_modes(self, tmp_path):
        for mode in ("fallback", "always", "hybrid", "never"):
            config_file = tmp_path / f"config_{mode}.toml"
            config_file.write_text(f'[completion]\nmode = "{mode}"\n')
            config = load_config(config_file)
            assert config["_completion_mode"] == mode

    def test_load_config_rejects_invalid_mode(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[completion]\nmode = "bogus"\n')
        config = load_config(config_file)
        assert config["_completion_mode"] == "hybrid"

    def test_emit_modes_in_output(self):
        config = load_config()
        for mode in ("fallback", "always", "hybrid", "never"):
            config["_completion_mode"] = mode
            output = emit_zsh_config(config)
            assert f"_COPA_COMPLETION_MODE='{mode}'" in output


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


class TestCompositionConfig:
    """Test continue vs close composition key splitting."""

    def test_default_continue_exists(self):
        assert DEFAULT_CONTINUE == {"pipe", "chain", "redirect"}

    def test_default_continue_are_valid_suffix_actions(self):
        for action in DEFAULT_CONTINUE:
            assert action in SUFFIXES

    def test_load_config_has_continue_actions(self):
        config = load_config()
        assert config["_continue_actions"] == {"pipe", "chain", "redirect"}

    def test_load_config_parses_composition_section(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[composition]\ncontinue = ["pipe"]\n')
        config = load_config(config_file)
        assert config["_continue_actions"] == {"pipe"}

    def test_load_config_empty_continue_list(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[composition]\ncontinue = []\n')
        config = load_config(config_file)
        assert config["_continue_actions"] == set()

    def test_load_config_ignores_invalid_continue_actions(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[composition]\ncontinue = ["pipe", "bogus", "chain"]\n')
        config = load_config(config_file)
        assert config["_continue_actions"] == {"pipe", "chain"}

    def test_emit_splits_suffixes(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_CLOSE_SUFFIXES" in output
        assert "_COPA_CONTINUE_SUFFIXES" in output

    def test_emit_continue_keys_not_in_expect(self):
        config = load_config()
        output = emit_zsh_config(config)
        # Default continue: pipe(ctrl-x), chain(ctrl-a), redirect(ctrl-t)
        # These should NOT be in _COPA_EXPECT
        for line in output.split("\n"):
            if line.startswith("_COPA_EXPECT="):
                assert "ctrl-x" not in line
                assert "ctrl-a" not in line
                assert "ctrl-t" not in line
                # Close keys should still be there
                assert "ctrl-v" in line
                assert "ctrl-o" in line
                assert "ctrl-/" in line
                break
        else:
            raise AssertionError("_COPA_EXPECT not found in output")

    def test_emit_continue_suffixes_correct(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_CONTINUE_SUFFIXES[ctrl-x]=' | '" in output
        assert "_COPA_CONTINUE_SUFFIXES[ctrl-a]=' && '" in output
        assert "_COPA_CONTINUE_SUFFIXES[ctrl-t]=' > '" in output

    def test_emit_close_suffixes_correct(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_CLOSE_SUFFIXES[ctrl-v]=' &'" in output
        assert "_COPA_CLOSE_SUFFIXES[ctrl-o]=' 2>&1'" in output
        assert "_COPA_CLOSE_SUFFIXES[ctrl-/]=' 2>/dev/null'" in output

    def test_empty_continue_all_keys_close(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[composition]\ncontinue = []\n')
        config = load_config(config_file)
        output = emit_zsh_config(config)
        # All 6 keys should be in _COPA_EXPECT
        for line in output.split("\n"):
            if line.startswith("_COPA_EXPECT="):
                assert "ctrl-v" in line
                assert "ctrl-o" in line
                assert "ctrl-x" in line
                assert "ctrl-t" in line
                assert "ctrl-a" in line
                assert "ctrl-/" in line
                break
        # No continue suffixes should be emitted
        assert "_COPA_CONTINUE_SUFFIXES[" not in output

    def test_all_continue_no_expect_keys(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[composition]\ncontinue = ["pipe", "chain", "redirect", "background", "merge_output", "suppress"]\n'
        )
        config = load_config(config_file)
        output = emit_zsh_config(config)
        for line in output.split("\n"):
            if line.startswith("_COPA_EXPECT="):
                assert line == "_COPA_EXPECT=''"
                break


class TestSelectKeyConfig:
    """Test select key (Ctrl-B) for multi-select mode."""

    def test_select_in_defaults(self):
        assert "select" in DEFAULT_KEYS
        assert DEFAULT_KEYS["select"] == "ctrl-b"

    def test_select_label(self):
        assert "select" in LABELS
        assert LABELS["select"] == "sel"

    def test_load_config_includes_select(self):
        config = load_config()
        assert config["select"] == "ctrl-b"

    def test_emit_zsh_config_has_select_key(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_SELECT_KEY='ctrl-b'" in output

    def test_header_row2_has_select_label(self):
        config = load_config()
        output = emit_zsh_config(config)
        for line in output.split("\n"):
            if line.startswith("_COPA_HEADER="):
                assert "^B:sel" in line
                break
        else:
            raise AssertionError("_COPA_HEADER not found in output")

    def test_select_key_override(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[keys]\nselect = "ctrl-j"\n')
        config = load_config(config_file)
        assert config["select"] == "ctrl-j"
        output = emit_zsh_config(config)
        assert "_COPA_SELECT_KEY='ctrl-j'" in output


class TestLayoutConfig:
    """Test [layout] section for height and preview_size."""

    def test_default_height_not_in_config(self):
        config = load_config()
        assert "_height" not in config  # uses default in emit

    def test_default_preview_size_not_in_config(self):
        config = load_config()
        assert "_preview_size" not in config  # uses default in emit

    def test_emit_default_height(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_HEIGHT='80%'" in output

    def test_emit_default_preview_size(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_PREVIEW_SIZE='40%'" in output

    def test_load_config_parses_height(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[layout]\nheight = "50%"\n')
        config = load_config(config_file)
        assert config["_height"] == "50%"

    def test_load_config_parses_preview_size(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[layout]\npreview_size = "60%"\n')
        config = load_config(config_file)
        assert config["_preview_size"] == "60%"

    def test_load_config_integer_height(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[layout]\nheight = 100\n')
        config = load_config(config_file)
        assert config["_height"] == "100"

    def test_emit_custom_values(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[layout]\nheight = "50%"\npreview_size = "60%"\n')
        config = load_config(config_file)
        output = emit_zsh_config(config)
        assert "_COPA_HEIGHT='50%'" in output
        assert "_COPA_PREVIEW_SIZE='60%'" in output

    def test_load_config_ignores_invalid_layout(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('layout = "not a table"\n')
        config = load_config(config_file)
        assert "_height" not in config


class TestBatchGroup:
    """Test the _batch-group hidden command."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_internal

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_internal, "get_db", lambda: db)
        return db

    def test_batch_group_assigns(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        id1 = db.add_command("cmd1")
        id2 = db.add_command("cmd2")
        runner = CliRunner()
        # Simulate tty input: group name "devops"
        with patch("copa.cli_internal._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["_batch-group", str(id1), str(id2)], input="devops\n")
        assert result.exit_code == 0
        assert db.get_command(id1).group_name == "devops"
        assert db.get_command(id2).group_name == "devops"

    def test_batch_group_cancel(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        id1 = db.add_command("cmd1")
        runner = CliRunner()
        with patch("copa.cli_internal._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["_batch-group", str(id1)], input="q\n")
        assert result.exit_code == 0
        assert db.get_command(id1).group_name is None

    def test_batch_group_no_ids(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["_batch-group"])
        assert result.exit_code == 0


class TestBatchDelete:
    """Test the _batch-delete hidden command."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_internal

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_internal, "get_db", lambda: db)
        return db

    def test_batch_delete_confirms(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        id1 = db.add_command("cmd1")
        id2 = db.add_command("cmd2")
        runner = CliRunner()
        with patch("copa.cli_internal._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["_batch-delete", str(id1), str(id2)], input="y\n")
        assert result.exit_code == 0
        assert db.get_command(id1) is None
        assert db.get_command(id2) is None

    def test_batch_delete_cancel(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        id1 = db.add_command("cmd1")
        runner = CliRunner()
        with patch("copa.cli_internal._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["_batch-delete", str(id1)], input="n\n")
        assert result.exit_code == 0
        assert db.get_command(id1) is not None

    def test_batch_delete_no_ids(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["_batch-delete"])
        assert result.exit_code == 0


class TestBatchDescribe:
    """Test the _batch-describe hidden command."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_internal

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_internal, "get_db", lambda: db)
        return db

    def test_batch_describe_generates(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        id1 = db.add_command("ls -la")
        id2 = db.add_command("git status")
        runner = CliRunner()
        with patch("copa.cli_internal._open_tty", return_value=(None, None)):
            with patch("copa.llm.generate_description", return_value="test desc"):
                result = runner.invoke(cli, ["_batch-describe", str(id1), str(id2)])
        assert result.exit_code == 0
        assert db.get_command(id1).description == "test desc"
        assert db.get_command(id2).description == "test desc"

    def test_batch_describe_no_ids(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["_batch-describe"])
        assert result.exit_code == 0


class TestDescribePrompt:
    """Test the prompt-first describe flow."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_llm

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_llm, "get_db", lambda: db)
        return db

    def test_manual_text_saves_directly(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        with patch("copa.cli_llm._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["describe", str(cmd_id)], input="my description\n")
        assert result.exit_code == 0
        assert db.get_command(cmd_id).description == "my description"

    def test_quit_with_q(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        with patch("copa.cli_llm._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["describe", str(cmd_id)], input="q\n")
        assert result.exit_code == 0
        assert db.get_command(cmd_id).description == ""

    def test_empty_input_quits(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("echo hello")
        runner = CliRunner()
        with patch("copa.cli_llm._open_tty", return_value=(None, None)):
            result = runner.invoke(cli, ["describe", str(cmd_id)], input="\n")
        assert result.exit_code == 0
        assert db.get_command(cmd_id).description == ""

    def test_auto_triggers_llm(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("ls -la")
        runner = CliRunner()
        with patch("copa.cli_llm._open_tty", return_value=(None, None)):
            with patch("copa.llm.generate_description", return_value="list files") as mock_gen:
                # "a" triggers LLM, then Enter accepts suggestion
                result = runner.invoke(cli, ["describe", str(cmd_id)], input="a\n\n")
        assert result.exit_code == 0
        mock_gen.assert_called_once()
        assert db.get_command(cmd_id).description == "list files"

    def test_auto_override_suggestion(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("ls -la")
        runner = CliRunner()
        with patch("copa.cli_llm._open_tty", return_value=(None, None)):
            with patch("copa.llm.generate_description", return_value="list files"):
                # "a" triggers LLM, then type override
                result = runner.invoke(cli, ["describe", str(cmd_id)], input="a\nmy override\n")
        assert result.exit_code == 0
        assert db.get_command(cmd_id).description == "my override"

    def test_auto_quit_after_suggestion(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        cmd_id = db.add_command("ls -la")
        runner = CliRunner()
        with patch("copa.cli_llm._open_tty", return_value=(None, None)):
            with patch("copa.llm.generate_description", return_value="list files"):
                result = runner.invoke(cli, ["describe", str(cmd_id)], input="a\nq\n")
        assert result.exit_code == 0
        assert db.get_command(cmd_id).description == ""

    def test_command_not_found(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["describe", "99999"])
        assert result.exit_code != 0


class TestSuggestConfig:
    """Test [suggest] section in config."""

    def test_default_suggest_enabled(self):
        config = load_config()
        assert config["_suggest_enabled"] is True

    def test_default_suggest_min_length(self):
        config = load_config()
        assert config["_suggest_min_length"] == 2

    def test_emit_zsh_config_has_suggest_vars(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_SUGGEST_ENABLED='true'" in output
        assert "_COPA_SUGGEST_MIN_LENGTH='2'" in output

    def test_load_config_suggest_disabled(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\nenabled = false\n")
        config = load_config(config_file)
        assert config["_suggest_enabled"] is False

    def test_emit_suggest_disabled(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\nenabled = false\n")
        config = load_config(config_file)
        output = emit_zsh_config(config)
        assert "_COPA_SUGGEST_ENABLED='false'" in output

    def test_load_config_suggest_min_length(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\nmin_length = 5\n")
        config = load_config(config_file)
        assert config["_suggest_min_length"] == 5

    def test_emit_suggest_min_length(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\nmin_length = 3\n")
        config = load_config(config_file)
        output = emit_zsh_config(config)
        assert "_COPA_SUGGEST_MIN_LENGTH='3'" in output

    def test_load_config_rejects_zero_min_length(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\nmin_length = 0\n")
        config = load_config(config_file)
        assert config["_suggest_min_length"] == 2  # default preserved

    def test_load_config_ignores_invalid_suggest(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('suggest = "not a table"\n')
        config = load_config(config_file)
        assert config["_suggest_enabled"] is True
        assert config["_suggest_min_length"] == 2


class TestSuggestCommand:
    """Test the _suggest hidden command."""

    def _make_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        db.init_db()
        import copa.cli_common
        import copa.cli_internal

        monkeypatch.setattr(copa.cli_common, "get_db", lambda: db)
        monkeypatch.setattr(copa.cli_internal, "get_db", lambda: db)
        return db

    def test_returns_best_match(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        now = time.time()
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("git push origin main", 10, now, now, "history"),
        )
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("git pull origin main", 5, now, now, "history"),
        )
        db.conn.commit()
        runner = CliRunner()
        result = runner.invoke(cli, ["_suggest", "git pu"])
        assert result.exit_code == 0
        assert result.output.strip() in ("git push origin main", "git pull origin main")

    def test_no_match_returns_empty(self, tmp_path, monkeypatch):
        self._make_db(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli, ["_suggest", "zzz"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_exact_match_returns_empty(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        now = time.time()
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("git push origin main", 10, now, now, "history"),
        )
        db.conn.commit()
        runner = CliRunner()
        result = runner.invoke(cli, ["_suggest", "git push origin main"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_picks_highest_scored(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        now = time.time()
        # High frequency, recent
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("docker compose up -d", 100, now, now, "history"),
        )
        # Low frequency, old
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("docker compose down", 1, now - 86400 * 30, now - 86400 * 30, "history"),
        )
        db.conn.commit()
        runner = CliRunner()
        result = runner.invoke(cli, ["_suggest", "docker"])
        assert result.exit_code == 0
        assert result.output.strip() == "docker compose up -d"

    def test_suggest_after_backspace_prefix(self, tmp_path, monkeypatch):
        """Simulate the backspace scenario: user types 'git push', backspaces to 'git pu',
        then re-queries. The _suggest command itself should still return a match —
        the latch suppression happens in the ZLE shell layer, not the CLI."""
        db = self._make_db(tmp_path, monkeypatch)
        now = time.time()
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("git push origin main", 10, now, now, "history"),
        )
        db.conn.commit()
        runner = CliRunner()
        # After backspace the buffer would be "git pus" — CLI still returns match
        result = runner.invoke(cli, ["_suggest", "git pus"])
        assert result.exit_code == 0
        assert result.output.strip() == "git push origin main"

    def test_handles_sql_wildcards_in_prefix(self, tmp_path, monkeypatch):
        db = self._make_db(tmp_path, monkeypatch)
        now = time.time()
        db.conn.execute(
            "INSERT INTO commands (command, frequency, last_used, first_added, source) VALUES (?, ?, ?, ?, ?)",
            ("test_command", 5, now, now, "history"),
        )
        db.conn.commit()
        runner = CliRunner()
        # % and _ should be escaped, not treated as wildcards
        result = runner.invoke(cli, ["_suggest", "test%"])
        assert result.exit_code == 0
        assert result.output.strip() == ""


class TestSuggestBackspaceLatch:
    """Test that the backspace latch mechanism is present in shell integration files.

    The latch suppresses inline suggestions after Backspace until Tab re-enables them.
    This is shell-level behavior (ZLE widgets), so we verify the .zsh files contain
    the correct latch variable and logic rather than testing ZLE directly.
    """

    @staticmethod
    def _read_zsh(name: str) -> str:
        root = Path(__file__).resolve().parent.parent
        return (root / name).read_text()

    def test_packaged_zsh_has_latch_variable(self):
        content = self._read_zsh("copa/copa.zsh")
        assert "_COPA_SUGGEST_LATCHED=0" in content

    def test_root_zsh_has_latch_variable(self):
        content = self._read_zsh("copa.zsh")
        assert "_COPA_SUGGEST_LATCHED=0" in content

    def test_packaged_zsh_backspace_sets_latch(self):
        content = self._read_zsh("copa/copa.zsh")
        # backward-delete-char should set latch=1 and clear, NOT call fetch
        assert "_copa_suggest_backward_delete_char()" in content
        # Find the function body
        start = content.index("_copa_suggest_backward_delete_char()")
        func_block = content[start : start + 200]
        assert "_COPA_SUGGEST_LATCHED=1" in func_block
        assert "_copa_suggest_clear" in func_block
        assert "_copa_suggest_fetch" not in func_block

    def test_root_zsh_backspace_sets_latch(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_backward_delete_char()")
        func_block = content[start : start + 200]
        assert "_COPA_SUGGEST_LATCHED=1" in func_block
        assert "_copa_suggest_clear" in func_block
        assert "_copa_suggest_fetch" not in func_block

    def test_packaged_zsh_fetch_checks_latch(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_fetch()")
        func_block = content[start : start + 400]
        assert "_COPA_SUGGEST_LATCHED" in func_block

    def test_packaged_zsh_tab_unlatches(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_expand_or_complete()")
        func_block = content[start : start + 800]
        assert "_COPA_SUGGEST_LATCHED=0" in func_block

    def test_packaged_zsh_backward_kill_word_latches(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_backward_kill_word()")
        func_block = content[start : start + 200]
        assert "_COPA_SUGGEST_LATCHED=1" in func_block

    def test_packaged_zsh_enter_resets_latch(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_accept_line()")
        func_block = content[start : start + 200]
        assert "_COPA_SUGGEST_LATCHED=0" in func_block


class TestTabAcceptConfig:
    """Test [suggest] tab_accept config option."""

    def test_default_tab_accept_is_2(self):
        config = load_config()
        assert config["_suggest_tab_accept"] == 2

    def test_emit_zsh_config_has_tab_accept(self):
        config = load_config()
        output = emit_zsh_config(config)
        assert "_COPA_SUGGEST_TAB_ACCEPT='2'" in output

    def test_load_config_tab_accept_1(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\ntab_accept = 1\n")
        config = load_config(config_file)
        assert config["_suggest_tab_accept"] == 1

    def test_emit_tab_accept_1(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\ntab_accept = 1\n")
        config = load_config(config_file)
        output = emit_zsh_config(config)
        assert "_COPA_SUGGEST_TAB_ACCEPT='1'" in output

    def test_load_config_tab_accept_2(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\ntab_accept = 2\n")
        config = load_config(config_file)
        assert config["_suggest_tab_accept"] == 2

    def test_load_config_rejects_invalid_tab_accept(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\ntab_accept = 3\n")
        config = load_config(config_file)
        assert config["_suggest_tab_accept"] == 2  # default preserved

    def test_load_config_rejects_zero_tab_accept(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[suggest]\ntab_accept = 0\n")
        config = load_config(config_file)
        assert config["_suggest_tab_accept"] == 2

    def test_load_config_rejects_string_tab_accept(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[suggest]\ntab_accept = "fast"\n')
        config = load_config(config_file)
        assert config["_suggest_tab_accept"] == 2


class TestTabAcceptZsh:
    """Test that .zsh files contain tab_accept logic with completion menu hoisting."""

    @staticmethod
    def _read_zsh(name: str) -> str:
        root = Path(__file__).resolve().parent.parent
        return (root / name).read_text()

    def test_packaged_zsh_has_tab_accept_fallback(self):
        content = self._read_zsh("copa/copa.zsh")
        assert "_COPA_SUGGEST_TAB_ACCEPT='2'" in content

    def test_root_zsh_has_tab_accept_fallback(self):
        content = self._read_zsh("copa.zsh")
        assert "_COPA_SUGGEST_TAB_ACCEPT='2'" in content

    def test_packaged_zsh_has_pending_variable(self):
        content = self._read_zsh("copa/copa.zsh")
        assert '_COPA_SUGGEST_PENDING=""' in content

    def test_root_zsh_has_pending_variable(self):
        content = self._read_zsh("copa.zsh")
        assert '_COPA_SUGGEST_PENDING=""' in content

    def test_packaged_zsh_tab_checks_accept_mode(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_expand_or_complete()")
        func_block = content[start : start + 800]
        # Tab widget checks tab_accept internally for mode 1 vs 2
        assert "_COPA_SUGGEST_TAB_ACCEPT" in func_block
        assert "_copa_suggest_clear" in func_block
        assert "zle menu-complete" in func_block
        # Mode 2 sets pending and opens completion menu
        assert "_COPA_SUGGEST_PENDING" in func_block
        # Tab is bound via bindkey, not by overriding expand-or-complete
        assert "bindkey '^I' _copa_suggest_expand_or_complete" in content

    def test_root_zsh_tab_checks_accept_mode(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_expand_or_complete()")
        func_block = content[start : start + 800]
        assert "_COPA_SUGGEST_TAB_ACCEPT" in func_block
        assert "_copa_suggest_clear" in func_block
        assert "zle menu-complete" in func_block
        assert "_COPA_SUGGEST_PENDING" in func_block
        assert "bindkey '^I' _copa_suggest_expand_or_complete" in content

    def test_packaged_zsh_down_opens_menu_or_history(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_down_line_or_history()")
        func_block = content[start : start + 400]
        assert "_copa_suggest_clear" in func_block
        assert ".down-line-or-history" in func_block
        # Down arrow with suggestion: hoists to completion menu
        assert "_COPA_SUGGEST_PENDING" in func_block
        assert "zle menu-complete" in func_block

    def test_root_zsh_down_opens_menu_or_history(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_down_line_or_history()")
        func_block = content[start : start + 400]
        assert "_copa_suggest_clear" in func_block
        assert ".down-line-or-history" in func_block
        assert "_COPA_SUGGEST_PENDING" in func_block
        assert "zle menu-complete" in func_block

    def test_packaged_zsh_clear_resets_pending(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_clear()")
        func_block = content[start : start + 200]
        assert '_COPA_SUGGEST_PENDING=""' in func_block

    def test_root_zsh_clear_resets_pending(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_clear()")
        func_block = content[start : start + 200]
        assert '_COPA_SUGGEST_PENDING=""' in func_block

    def test_packaged_zsh_fetch_resets_pending(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_fetch()")
        func_block = content[start : start + 400]
        assert '_COPA_SUGGEST_PENDING=""' in func_block

    def test_root_zsh_fetch_resets_pending(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_fetch()")
        func_block = content[start : start + 400]
        assert '_COPA_SUGGEST_PENDING=""' in func_block

    def test_packaged_zsh_down_search_clears_suggestion(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_down_line_or_search()")
        func_block = content[start : start + 400]
        assert "_copa_suggest_clear" in func_block
        assert ".down-line-or-search" in func_block

    def test_root_zsh_down_search_clears_suggestion(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_down_line_or_search()")
        func_block = content[start : start + 400]
        assert "_copa_suggest_clear" in func_block
        assert ".down-line-or-search" in func_block

    def test_packaged_zsh_unlatch_fetches_for_mode1(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_suggest_expand_or_complete()")
        func_block = content[start : start + 900]
        latch_idx = func_block.index("_COPA_SUGGEST_LATCHED=0")
        after_latch = func_block[latch_idx:]
        # Mode 1: unlatch → fetch → return (show ghost text, wait for next Tab)
        assert "_copa_suggest_fetch" in after_latch

    def test_root_zsh_unlatch_fetches_for_mode1(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_suggest_expand_or_complete()")
        func_block = content[start : start + 900]
        latch_idx = func_block.index("_COPA_SUGGEST_LATCHED=0")
        after_latch = func_block[latch_idx:]
        assert "_copa_suggest_fetch" in after_latch

    def test_packaged_zsh_history_complete_hoists_suggestion(self):
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_history_complete()")
        func_block = content[start : start + 800]
        assert "_COPA_SUGGEST_PENDING" in func_block
        assert "compadd -U -Q -V 'copa-suggestion'" in func_block

    def test_root_zsh_history_complete_hoists_suggestion(self):
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_history_complete()")
        func_block = content[start : start + 800]
        assert "_COPA_SUGGEST_PENDING" in func_block
        assert "compadd -U -Q -V 'copa-suggestion'" in func_block

    def test_packaged_zsh_forces_completion_list(self):
        """compstate[list] forces the completion list to display."""
        content = self._read_zsh("copa/copa.zsh")
        start = content.index("_copa_history_complete()")
        func_block = content[start : start + 800]
        assert "compstate[list]='list force'" in func_block

    def test_root_zsh_forces_completion_list(self):
        """compstate[list] forces the completion list to display."""
        content = self._read_zsh("copa.zsh")
        start = content.index("_copa_history_complete()")
        func_block = content[start : start + 800]
        assert "compstate[list]='list force'" in func_block

    def test_packaged_zsh_has_suggestion_branding(self):
        content = self._read_zsh("copa/copa.zsh")
        assert "copa-suggestion" in content
        assert "-X 'SUGGESTED'" in content

    def test_root_zsh_has_suggestion_branding(self):
        content = self._read_zsh("copa.zsh")
        assert "copa-suggestion" in content
        assert "-X 'SUGGESTED'" in content
