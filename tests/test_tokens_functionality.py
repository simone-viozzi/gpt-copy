#!/usr/bin/env python3
"""Tests for token counting functionality in gpt-copy."""

import tempfile
import pytest
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gpt_copy.gpt_copy import (
    count_tokens_safe,
    collect_file_info,
    generate_tree,
    get_ignore_settings,
)


class TestTokensCounting:
    """Test token counting functionality."""

    def test_count_tokens_safe_simple(self):
        """Test basic token counting."""
        # Test simple cases
        assert count_tokens_safe("Hello world") > 0
        assert count_tokens_safe("") == 1  # Minimum of 1 token

        # Test that more text gives more tokens
        short_text = "Hello"
        long_text = "Hello world this is a much longer piece of text that should have more tokens"
        assert count_tokens_safe(long_text) > count_tokens_safe(short_text)

    def test_collect_file_info(self):
        """Test collecting file information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "short.py").write_text("print('hi')")
            (temp_path / "long.py").write_text(
                "# This is a much longer file with more content\nprint('hello world')\n# More comments"
            )
            (temp_path / "empty.txt").write_text("")

            # Get ignore settings
            gitignore_specs, tracked_files = get_ignore_settings(temp_path, force=True)

            # Collect file info (no filter engine = include all)
            file_infos = collect_file_info(
                temp_path,
                gitignore_specs,
                tracked_files,
                filter_engine=None,
            )

            # Check results
            assert len(file_infos) == 3

            # Find specific files
            short_file = next(f for f in file_infos if f.relative_path == "short.py")
            long_file = next(f for f in file_infos if f.relative_path == "long.py")
            empty_file = next(f for f in file_infos if f.relative_path == "empty.txt")

            # Verify files are collected
            assert short_file.relative_path == "short.py"
            assert long_file.relative_path == "long.py"
            assert empty_file.relative_path == "empty.txt"

    def test_generate_tree_with_tokens(self):
        """Test generating tree structure with token counts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.py").write_text("print('test1')")
            (temp_path / "file2.py").write_text("print('test2 with more content')")

            # Get ignore settings
            gitignore_specs, tracked_files = get_ignore_settings(temp_path, force=True)

            # Collect file infos
            file_infos = collect_file_info(
                temp_path,
                gitignore_specs,
                tracked_files,
                filter_engine=None,
            )

            # Generate tree with tokens
            tree_output = generate_tree(
                temp_path,
                file_infos,
                with_tokens=True,
            )

            # Check output contains token counts
            assert "tokens" in tree_output
            assert "file1.py" in tree_output
            assert "file2.py" in tree_output

    def test_generate_tree_with_tokens_top_n(self):
        """Test generating tree with top-N filtering and correct ordering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files with different sizes
            (temp_path / "small.py").write_text("x")
            (temp_path / "medium.py").write_text("x" * 10)
            (temp_path / "large.py").write_text("x" * 20)
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "huge.py").write_text("x" * 30)

            # Get ignore settings
            gitignore_specs, tracked_files = get_ignore_settings(temp_path, force=True)

            # Collect file infos
            file_infos = collect_file_info(
                temp_path,
                gitignore_specs,
                tracked_files,
                filter_engine=None,
            )

            # Generate tree with top-3
            tree_output = generate_tree(
                temp_path,
                file_infos,
                with_tokens=True,
                top_n=3,
            )

            # Check only top 3 files are included and in correct order
            assert "huge.py" in tree_output
            assert "large.py" in tree_output
            assert "medium.py" in tree_output
            assert "small.py" not in tree_output
            assert "Showing top 3 files" in tree_output

            # Verify ordering: huge.py should appear before large.py, large.py before medium.py
            huge_pos = tree_output.find("huge.py")
            large_pos = tree_output.find("large.py")
            medium_pos = tree_output.find("medium.py")
            assert huge_pos < large_pos < medium_pos, (
                f"Files not in correct order: huge at {huge_pos}, large at {large_pos}, medium at {medium_pos}"
            )

    def test_file_filtering_with_tokens(self):
        """Test that file filtering works with token counting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test.py").write_text("print('python')")
            (temp_path / "test.js").write_text("console.log('javascript')")
            (temp_path / "readme.txt").write_text("This is a readme file")

            # Get ignore settings
            gitignore_specs, tracked_files = get_ignore_settings(temp_path, force=True)

            # Create filter engine for Python files only
            from gpt_copy.filter import FilterEngine, Rule, RuleKind

            rules = [
                Rule(kind=RuleKind.EXCLUDE, pattern="**"),
                Rule(kind=RuleKind.INCLUDE, pattern="*.py"),
            ]
            filter_engine = FilterEngine(rules)

            # Collect only Python files
            file_infos = collect_file_info(
                temp_path,
                gitignore_specs,
                tracked_files,
                filter_engine=filter_engine,
            )

            # Should only have the Python file
            assert len(file_infos) == 1
            assert file_infos[0].relative_path == "test.py"


if __name__ == "__main__":
    pytest.main([__file__])
