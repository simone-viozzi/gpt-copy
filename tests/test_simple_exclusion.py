#!/usr/bin/env python3
"""Parametrized test for inclusion and exclusion pattern behavior."""

import tempfile
from pathlib import Path

import pytest

from gpt_copy.gpt_copy import generate_tree, collect_file_info
from gpt_copy.filter import FilterEngine, Rule, RuleKind


@pytest.mark.parametrize(
    "pattern_type,patterns,expected_in,expected_out",
    [
        # Exclusion patterns
        ("exclude", ["dropbox/file.txt"], ["dropbox", "other.txt"], ["file.txt"]),
        ("exclude", ["dropbox/*"], ["dropbox", "other.txt"], ["file.txt"]),
        ("exclude", ["dropbox"], ["other.txt"], []),  # dropbox shown compressed
        # Inclusion patterns - default is INCLUDE
        # To get "only txt files", must first exclude all, then include specific
        (
            "include",
            ["*.txt"],
            ["other.txt", "dropbox", "file.txt"],
            [],
        ),  # include matches *.txt (both files)
        (
            "include",
            ["dropbox/*"],
            ["dropbox", "file.txt", "other.txt"],
            [],
        ),  # include matches dropbox/* (file.txt)
        (
            "include",
            ["other.txt"],
            ["other.txt", "dropbox", "file.txt"],
            [],
        ),  # include matches other.txt
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

        # Create filter engine based on pattern type
        rules = []
        if pattern_type == "exclude":
            for pattern in patterns:
                rules.append(Rule(kind=RuleKind.EXCLUDE, pattern=pattern))
        else:  # include
            for pattern in patterns:
                rules.append(Rule(kind=RuleKind.INCLUDE, pattern=pattern))

        filter_engine = FilterEngine(rules) if rules else None

        # Collect file infos and generate tree
        file_infos = collect_file_info(temp_path, {}, None, filter_engine)
        result = generate_tree(
            temp_path, file_infos, with_tokens=False, filter_engine=filter_engine
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
