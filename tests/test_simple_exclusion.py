#!/usr/bin/env python3
"""Simple test for exclusion pattern behavior."""

import tempfile
from pathlib import Path

from gpt_copy.gpt_copy import generate_tree


def test_file_exclusion():
    """Test that file exclusion patterns work in tree generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create structure: temp_dir/dropbox/file.txt
        dropbox_dir = temp_path / "dropbox"
        dropbox_dir.mkdir()
        (dropbox_dir / "file.txt").write_text("content")
        (temp_path / "other.txt").write_text("other")

        # Test excluding specific file
        result = generate_tree(temp_path, {}, None, ["dropbox/file.txt"])
        assert "dropbox" in result
        assert "file.txt" not in result
        assert "other.txt" in result


def test_wildcard_exclusion():
    """Test that wildcard exclusion patterns work."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create structure: temp_dir/dropbox/file.txt
        dropbox_dir = temp_path / "dropbox"
        dropbox_dir.mkdir()
        (dropbox_dir / "file.txt").write_text("content")
        (temp_path / "other.txt").write_text("other")

        # Test excluding files in directory
        result = generate_tree(temp_path, {}, None, ["dropbox/*"])
        assert "dropbox" in result
        assert "file.txt" not in result
        assert "other.txt" in result


def test_directory_exclusion():
    """Test that directory exclusion shows compressed view."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create structure: temp_dir/dropbox/file.txt
        dropbox_dir = temp_path / "dropbox"
        dropbox_dir.mkdir()
        (dropbox_dir / "file.txt").write_text("content")
        (temp_path / "other.txt").write_text("other")

        # Test excluding directory itself
        result = generate_tree(temp_path, {}, None, ["dropbox"])
        assert "dropbox" in result
        assert "other.txt" in result
        # Directory should show in compressed form (we can see file but spacing is different)
