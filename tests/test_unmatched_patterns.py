#!/usr/bin/env python3
"""Tests for warning about unmatched patterns."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from gpt_copy.gpt_copy import main as gpt_copy_main
from gpt_copy.filter import FilterEngine, Rule, RuleKind


def test_filter_engine_tracks_unmatched_patterns():
    """Test that FilterEngine correctly tracks unmatched patterns."""
    rules = [
        Rule(kind=RuleKind.EXCLUDE, pattern="*.log"),
        Rule(kind=RuleKind.INCLUDE, pattern="*.txt"),
        Rule(kind=RuleKind.EXCLUDE, pattern="*.nonexistent"),
    ]
    engine = FilterEngine(rules)

    # Simulate matching some files
    engine.matches("*.log", "debug.log", is_dir=False)
    engine.matches("*.txt", "readme.txt", is_dir=False)

    # Get unmatched patterns
    unmatched = engine.get_unmatched_patterns()

    # Only *.nonexistent should be unmatched
    assert len(unmatched) == 1
    assert unmatched[0] == (RuleKind.EXCLUDE, "*.nonexistent")


def test_filter_engine_all_patterns_matched():
    """Test that no warning when all patterns match."""
    rules = [
        Rule(kind=RuleKind.EXCLUDE, pattern="*.log"),
        Rule(kind=RuleKind.INCLUDE, pattern="*.txt"),
    ]
    engine = FilterEngine(rules)

    # Simulate matching all patterns
    engine.matches("*.log", "debug.log", is_dir=False)
    engine.matches("*.txt", "readme.txt", is_dir=False)

    # Get unmatched patterns
    unmatched = engine.get_unmatched_patterns()

    # No patterns should be unmatched
    assert len(unmatched) == 0


def test_cli_warns_about_unmatched_exclude_pattern():
    """Test that CLI warns about unmatched exclude pattern."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file.txt").write_text("content")
        (temp_path / "readme.md").write_text("readme")

        runner = CliRunner()
        result = runner.invoke(
            gpt_copy_main,
            [str(temp_path), "--exclude", "*.nonexistent", "--tree-only"],
        )

        # Check that command succeeded
        assert result.exit_code == 0

        # Check that warning is in stderr
        assert (
            "Warning: The following patterns did not match any files:" in result.output
        )
        assert "--exclude '*.nonexistent'" in result.output


def test_cli_warns_about_unmatched_include_pattern():
    """Test that CLI warns about unmatched include pattern."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file.txt").write_text("content")
        (temp_path / "readme.md").write_text("readme")

        runner = CliRunner()
        result = runner.invoke(
            gpt_copy_main,
            [str(temp_path), "--include", "*.nonexistent", "--tree-only"],
        )

        # Check that command succeeded
        assert result.exit_code == 0

        # Check that warning is in stderr
        assert (
            "Warning: The following patterns did not match any files:" in result.output
        )
        assert "--include '*.nonexistent'" in result.output


def test_cli_warns_about_multiple_unmatched_patterns():
    """Test that CLI warns about multiple unmatched patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file.txt").write_text("content")

        runner = CliRunner()
        result = runner.invoke(
            gpt_copy_main,
            [
                str(temp_path),
                "--exclude",
                "*.log",
                "--exclude",
                "*.nonexistent",
                "--include",
                "*.doesntexist",
                "--tree-only",
            ],
        )

        # Check that command succeeded
        assert result.exit_code == 0

        # Check that warnings are in stderr
        assert (
            "Warning: The following patterns did not match any files:" in result.output
        )
        assert "--exclude '*.nonexistent'" in result.output
        assert "--include '*.doesntexist'" in result.output
        # *.log shouldn't appear because there are no .log files to match


def test_cli_no_warning_when_all_patterns_match():
    """Test that CLI doesn't warn when all patterns match."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file.txt").write_text("content")
        (temp_path / "readme.md").write_text("readme")

        runner = CliRunner()
        result = runner.invoke(
            gpt_copy_main,
            [str(temp_path), "--exclude", "*.md", "--tree-only"],
        )

        # Check that command succeeded
        assert result.exit_code == 0

        # Check that no warning is in output
        assert (
            "Warning: The following patterns did not match any files:"
            not in result.output
        )


def test_cli_warns_about_unmatched_exclude_dir():
    """Test that CLI warns about unmatched exclude-dir pattern."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "src").mkdir()
        (temp_path / "src" / "main.py").write_text("print('hello')")

        runner = CliRunner()
        result = runner.invoke(
            gpt_copy_main,
            [str(temp_path), "--exclude-dir", "nonexistent", "--tree-only"],
        )

        # Check that command succeeded
        assert result.exit_code == 0

        # Check that warning is in stderr (exclude-dir gets converted to exclude with /)
        assert (
            "Warning: The following patterns did not match any files:" in result.output
        )
        assert "--exclude 'nonexistent/'" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
