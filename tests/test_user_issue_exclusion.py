#!/usr/bin/env python3
"""
Tests for the user issue with inclusion/exclusion patterns.

This test validates the scenarios described in the issue where
directory exclusion patterns were not working correctly.
"""

import tempfile
from pathlib import Path

import pytest

from gpt_copy.gpt_copy import collect_file_info, generate_tree
from gpt_copy.filter import FilterEngine, Rule, RuleKind


def create_user_issue_structure(base_path: Path) -> None:
    """
    Create the directory structure from the user's issue.

    Structure:
        base_path/
        ├── app/
        │   └── file.txt
        ├── deployment/
        │   └── file.txt
        ├── frontend/
        │   └── file.txt
        ├── notebooks/
        │   └── file.txt
        ├── tests/
        │   └── file.txt
        ├── root.txt
        ├── uv.lock
        ├── .gitignore
        └── .pre-commit-config.yaml
    """
    # Create directories
    for dir_name in ["app", "deployment", "frontend", "notebooks", "tests"]:
        dir_path = base_path / dir_name
        dir_path.mkdir()
        (dir_path / "file.txt").write_text(f"{dir_name} content")

    # Create files in root
    (base_path / "root.txt").write_text("root content")
    (base_path / "uv.lock").write_text("lock content")
    (base_path / ".gitignore").write_text("# gitignore")
    (base_path / ".pre-commit-config.yaml").write_text("# pre-commit")


def test_exclude_dir_option():
    """
    Test --exclude-dir option excludes directories and their contents.

    This is the main scenario from the user's issue.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_user_issue_structure(temp_path)

        # Use --exclude-dir to exclude multiple directories
        rules = [
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="app"),
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="notebooks"),
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="frontend"),
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="tests"),
        ]
        filter_engine = FilterEngine(rules)

        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Check that excluded directories' files are not in file_infos
        file_paths = [fi.relative_path for fi in file_infos if not fi.is_directory]
        assert "app/file.txt" not in file_paths
        assert "notebooks/file.txt" not in file_paths
        assert "frontend/file.txt" not in file_paths
        assert "tests/file.txt" not in file_paths

        # But deployment files should be included
        assert "deployment/file.txt" in file_paths

        # Root files should be included
        assert "root.txt" in file_paths
        assert "uv.lock" in file_paths


def test_exclude_with_trailing_slash():
    """
    Test -e with trailing slash excludes directories and their contents.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_user_issue_structure(temp_path)

        # Use -e with trailing slash
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="app/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="notebooks/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="frontend/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="tests/"),
        ]
        filter_engine = FilterEngine(rules)

        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Check that excluded directories' files are not in file_infos
        file_paths = [fi.relative_path for fi in file_infos if not fi.is_directory]
        assert "app/file.txt" not in file_paths
        assert "notebooks/file.txt" not in file_paths
        assert "frontend/file.txt" not in file_paths
        assert "tests/file.txt" not in file_paths

        # But deployment files should be included
        assert "deployment/file.txt" in file_paths


def test_exclude_with_include_override():
    """
    Test that -i can override -e to include specific directories.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_user_issue_structure(temp_path)

        # Exclude app, but then include deployment specifically
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="app/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="notebooks/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="frontend/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="tests/"),
            Rule(kind=RuleKind.INCLUDE, pattern="deployment/**"),
        ]
        filter_engine = FilterEngine(rules)

        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Deployment should definitely be included due to explicit include
        file_paths = [fi.relative_path for fi in file_infos if not fi.is_directory]
        assert "deployment/file.txt" in file_paths

        # Others should be excluded
        assert "app/file.txt" not in file_paths
        assert "notebooks/file.txt" not in file_paths


def test_tree_shows_excluded_dirs_without_children():
    """
    Test that excluded directories appear in tree but without their children.

    This is important for users to see what directories exist, even if excluded.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_user_issue_structure(temp_path)

        rules = [
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="app"),
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="notebooks"),
        ]
        filter_engine = FilterEngine(rules)

        file_infos = collect_file_info(temp_path, {}, None, filter_engine)
        tree_output = generate_tree(
            temp_path, file_infos, with_tokens=False, filter_engine=filter_engine
        )

        # Excluded directories should appear in tree
        assert "app" in tree_output
        assert "notebooks" in tree_output

        # But their children should NOT appear
        # (the children are excluded, so they're not in file_infos)
        # The tree shows the directory name but not the contents
        assert "app/file.txt" not in tree_output
        assert "notebooks/file.txt" not in tree_output

        # Non-excluded directories should show with contents
        assert "deployment" in tree_output
        assert "deployment/file.txt" in tree_output or "file.txt" in tree_output


def test_exclude_all_then_include_specific():
    """
    Test pattern: exclude everything, then include specific directories.

    This is a common use case for focusing on specific parts of a project.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_user_issue_structure(temp_path)

        # Exclude everything except deployment
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="**"),
            Rule(kind=RuleKind.INCLUDE, pattern="deployment/**"),
        ]
        filter_engine = FilterEngine(rules)

        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        file_paths = [fi.relative_path for fi in file_infos if not fi.is_directory]

        # Only deployment files should be included
        assert "deployment/file.txt" in file_paths

        # Everything else should be excluded
        assert "app/file.txt" not in file_paths
        assert "root.txt" not in file_paths
        assert "uv.lock" not in file_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
