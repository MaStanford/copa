"""Tests for fzf format_lines hidden field and format_preview flags."""

from copa.fzf import format_lines, format_preview
from copa.models import Command


class TestFormatLinesSearchField:
    """Test that format_lines includes a hidden 4th field with description+flags."""

    def test_four_fields_present(self):
        cmd = Command(id=1, command="echo hi", description="Say hello", frequency=5)
        lines = format_lines([cmd])
        assert len(lines) == 1
        parts = lines[0].split("┃")
        assert len(parts) == 4, f"Expected 4 fields, got {len(parts)}: {lines[0]}"

    def test_hidden_field_contains_description(self):
        cmd = Command(id=1, command="adb cmd", description="Enable Bluetooth", frequency=1)
        lines = format_lines([cmd])
        field4 = lines[0].split("┃")[3]
        assert "Enable Bluetooth" in field4

    def test_hidden_field_contains_flags(self):
        cmd = Command(
            id=1,
            command="flash",
            description="Flash it",
            flags={"--wipe": "Wipe userdata", "-v": "Verbose"},
            frequency=1,
        )
        lines = format_lines([cmd])
        field4 = lines[0].split("┃")[3]
        assert "--wipe" in field4
        assert "Wipe userdata" in field4
        assert "-v" in field4
        assert "Verbose" in field4

    def test_hidden_field_empty_when_no_metadata(self):
        cmd = Command(id=1, command="ls", frequency=1)
        lines = format_lines([cmd])
        field4 = lines[0].split("┃")[3].strip()
        assert field4 == ""

    def test_command_still_in_field2(self):
        cmd = Command(id=1, command="git push", frequency=1)
        lines = format_lines([cmd])
        field2 = lines[0].split("┃")[1]
        assert "git push" in field2

    def test_id_in_field1(self):
        cmd = Command(id=42, command="test", frequency=1)
        lines = format_lines([cmd])
        field1 = lines[0].split("┃")[0]
        assert "42" in field1

    def test_multiple_commands(self):
        cmds = [
            Command(id=1, command="cmd1", description="desc1", frequency=1),
            Command(id=2, command="cmd2", description="desc2", flags={"--flag": "Flag desc"}, frequency=2),
        ]
        lines = format_lines(cmds)
        assert len(lines) == 2
        assert "desc1" in lines[0].split("┃")[3]
        assert "--flag" in lines[1].split("┃")[3]
        assert "Flag desc" in lines[1].split("┃")[3]

    def test_empty_list(self):
        assert format_lines([]) == []


class TestFormatPreviewFlags:
    """Test that format_preview shows flags section."""

    def test_no_flags_no_section(self):
        cmd = Command(id=1, command="echo hi", description="Say hello", frequency=1)
        preview = format_preview(cmd)
        assert "Flags:" not in preview

    def test_flags_shown(self):
        cmd = Command(
            id=1,
            command="flash",
            description="Flash it",
            flags={"--wipe": "Wipe userdata", "-v": "Verbose"},
            frequency=1,
        )
        preview = format_preview(cmd)
        assert "Flags:" in preview
        assert "--wipe" in preview
        assert "Wipe userdata" in preview
        assert "-v" in preview
        assert "Verbose" in preview

    def test_flags_section_alignment(self):
        cmd = Command(id=1, command="test", description="Test", flags={"--long-flag-name": "Description"}, frequency=1)
        preview = format_preview(cmd)
        lines = preview.split("\n")
        flag_lines = [line for line in lines if "--long-flag-name" in line]
        assert len(flag_lines) == 1
        # Should be indented
        assert flag_lines[0].startswith("  ")

    def test_preview_still_shows_description(self):
        cmd = Command(id=1, command="test", description="Test description", flags={"--flag": "desc"}, frequency=1)
        preview = format_preview(cmd)
        assert "Test description" in preview
        assert "Command:" in preview
        assert "Frequency:" in preview
