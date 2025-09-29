#!/usr/bin/env python3
"""Parametrized test for inclusion and exclusion pattern behavior."""

import tempfile
from pathlib import Path

import pytest

from gpt_copy.gpt_copy import generate_tree, collect_file_info


@pytest.mark.parametrize(
    "pattern_type,patterns,expected_in,expected_out",
    [
        # Exclusion patterns
        ("exclude", ["dropbox/file.txt"], ["dropbox", "other.txt"], ["file.txt"]),
        ("exclude", ["dropbox/*"], ["dropbox", "other.txt"], ["file.txt"]),
        ("exclude", ["dropbox"], ["other.txt"], []),  # dropbox shown compressed
        # Inclusion patterns
        ("include", ["*.txt"], ["other.txt"], ["dropbox"]),  # only txt files included
        ("include", ["dropbox/*"], ["dropbox", "file.txt"], ["other.txt"]),
        ("include", ["other.txt"], ["other.txt"], ["dropbox", "file.txt"]),
    ],
)
def test_pattern_filtering(pattern_type, patterns, expected_in, expected_out):
    """Test that inclusion and exclusion patterns work correctly in tree generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test structure: temp_dir/dropbox/file.txt and temp_dir/other.txt
        dropbox_dir = temp_path / "dropbox"
        dropbox_dir.mkdir()
        (dropbox_dir / "file.txt").write_text("content")
        (temp_path / "other.txt").write_text("other")

        # Apply patterns based on type
        if pattern_type == "exclude":
            file_infos = collect_file_info(temp_path, {}, None, None, patterns)
            result = generate_tree(
                temp_path, file_infos, with_tokens=False, exclude_patterns=patterns
            )
        else:  # include
            file_infos = collect_file_info(temp_path, {}, None, patterns, None)
            result = generate_tree(
                temp_path, file_infos, with_tokens=False, exclude_patterns=None
            )

        # Check expected inclusions
        for item in expected_in:
            assert item in result, (
                f"{item} should be in result for {pattern_type} patterns {patterns}"
            )

        # Check expected exclusions
        for item in expected_out:
            if (
                item != "dropbox"
                or pattern_type != "exclude"
                or "dropbox" not in patterns
            ):
                # Special case: dropbox directory appears compressed when excluded
                assert item not in result, (
                    f"{item} should not be in result for {pattern_type} patterns {patterns}"
                )
