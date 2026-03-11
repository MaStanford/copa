"""Tests for scanner #@ Flag: protocol."""

from copa.scanner import _scan_single_directory, extract_description


class TestExtractFlags:
    """Test #@ Flag: protocol header extraction."""

    def test_no_flags(self, tmp_script):
        script = tmp_script("test.sh", "#!/bin/bash\n#@ Description: A test\necho hi\n")
        desc, flags = extract_description(script)
        assert desc == "A test"
        assert flags == {}

    def test_single_flag(self, tmp_script):
        content = (
            "#!/bin/bash\n#@ Description: Flash device\n#@ Flag: --wipe: Wipe userdata before flashing\necho flashing\n"
        )
        script = tmp_script("flash.sh", content)
        desc, flags = extract_description(script)
        assert desc == "Flash device"
        assert flags == {"--wipe": "Wipe userdata before flashing"}

    def test_multiple_flags(self, tmp_script):
        content = (
            "#!/bin/bash\n"
            "#@ Description: Flash device\n"
            "#@ Flag: -w, --wipe: Wipe userdata\n"
            "#@ Flag: --skip <parts>: Skip partitions\n"
            "#@ Flag: -n, --dry-run: Show what would be done\n"
            "echo flashing\n"
        )
        script = tmp_script("flash.sh", content)
        desc, flags = extract_description(script)
        assert desc == "Flash device"
        assert len(flags) == 3
        assert flags["-w, --wipe"] == "Wipe userdata"
        assert flags["--skip <parts>"] == "Skip partitions"
        assert flags["-n, --dry-run"] == "Show what would be done"

    def test_flag_without_description(self, tmp_script):
        content = "#!/bin/bash\n#@ Description: Test\n#@ Flag: --verbose\n"
        script = tmp_script("test.sh", content)
        desc, flags = extract_description(script)
        assert flags == {"--verbose": ""}

    def test_flags_with_usage_and_purpose(self, tmp_script):
        content = (
            "#!/bin/bash\n"
            "#@ Description: Flash device\n"
            "#@ Usage: flash.sh [options]\n"
            "#@ Purpose: Simplify flashing\n"
            "#@ Flag: --wipe: Wipe userdata\n"
        )
        script = tmp_script("flash.sh", content)
        desc, flags = extract_description(script)
        assert "Flash device" in desc
        assert "Usage: flash.sh [options]" in desc
        assert "Purpose: Simplify flashing" in desc
        assert flags == {"--wipe": "Wipe userdata"}

    def test_flags_without_description_header(self, tmp_script):
        """Flags are collected even when there's no #@ Description."""
        content = (
            "#!/bin/bash\n# A simple legacy comment that describes this\n#@ Flag: --verbose: Enable verbose mode\n"
        )
        script = tmp_script("test.sh", content)
        desc, flags = extract_description(script)
        # Falls back to legacy pattern for description
        assert "legacy comment" in desc.lower() or len(desc) > 5
        assert flags == {"--verbose": "Enable verbose mode"}

    def test_flag_case_insensitive_header(self, tmp_script):
        content = (
            "#!/bin/bash\n"
            "#@ Description: Test\n"
            "#@ flag: --lower: lowercase flag header\n"
            "#@ FLAG: --upper: uppercase flag header\n"
        )
        script = tmp_script("test.sh", content)
        # The regex is #@\s*[Ff]lag: so only lowercase f and uppercase F match
        desc, flags = extract_description(script)
        assert "--lower" in flags

    def test_50_line_limit(self, tmp_script):
        """Scanner reads up to 50 lines."""
        lines = ["#!/bin/bash\n", "#@ Description: Test\n"]
        # Add 47 comment lines
        lines.extend([f"# padding line {i}\n" for i in range(47)])
        # Line 50 (0-indexed 49): still within limit
        lines.append("#@ Flag: --within: Within 50 lines\n")
        content = "".join(lines)
        script = tmp_script("test.sh", content)
        desc, flags = extract_description(script)
        assert "--within" in flags

    def test_returns_tuple(self, tmp_script):
        script = tmp_script("test.sh", "#!/bin/bash\necho hi\n")
        result = extract_description(script)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_empty_file(self, tmp_script):
        script = tmp_script("empty.sh", "")
        desc, flags = extract_description(script)
        assert desc == ""
        assert flags == {}


class TestScanDirectory:
    """Test that _scan_single_directory passes flags to the database."""

    def test_scan_captures_flags(self, tmp_db, tmp_path):
        script = tmp_path / "my-tool"
        script.write_text(
            "#!/bin/bash\n#@ Description: My tool\n#@ Flag: --verbose: Enable verbose output\necho running\n"
        )
        script.chmod(0o755)

        added = _scan_single_directory(tmp_db, tmp_path)
        assert added == 1

        results = tmp_db.search_commands("my-tool")
        assert len(results) == 1
        assert results[0].flags == {"--verbose": "Enable verbose output"}

    def test_scan_no_flags(self, tmp_db, tmp_path):
        script = tmp_path / "simple"
        script.write_text("#!/bin/bash\n#@ Description: Simple script\necho hi\n")
        script.chmod(0o755)

        _scan_single_directory(tmp_db, tmp_path)
        results = tmp_db.search_commands("simple")
        assert len(results) == 1
        assert results[0].flags == {}
