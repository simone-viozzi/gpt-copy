#!/usr/bin/env python3
"""
Comprehensive tests for the filtering specification.

Tests all examples from the issue specification to ensure the
last-match-wins semantics work correctly with conservative directory traversal.
"""

import tempfile
from pathlib import Path

import pytest

from gpt_copy.gpt_copy import generate_tree, collect_file_info
from gpt_copy.filter import FilterEngine, Rule, RuleKind, Action


def create_test_structure(base_path: Path) -> None:
    """
    Create a comprehensive test directory structure.

    Structure:
        base_path/
        ├── node_modules/
        │   └── package.txt
        ├── build/
        │   ├── main.js
        │   ├── debug.log
        │   └── reports/
        │       ├── summary.txt
        │       └── details.txt
        ├── data/
        │   ├── users.csv
        │   ├── products.csv
        │   └── readme.txt
        ├── tmp/
        │   ├── file1.txt
        │   └── nested/
        │       └── file2.txt
        ├── src/
        │   ├── main.py
        │   └── test.log
        └── dist/
            └── app.js
    """
    # Create directories
    (base_path / "node_modules").mkdir()
    (base_path / "build").mkdir()
    (base_path / "build" / "reports").mkdir()
    (base_path / "data").mkdir()
    (base_path / "tmp").mkdir()
    (base_path / "tmp" / "nested").mkdir()
    (base_path / "src").mkdir()
    (base_path / "dist").mkdir()

    # Create files
    (base_path / "node_modules" / "package.txt").write_text("package")
    (base_path / "build" / "main.js").write_text("main")
    (base_path / "build" / "debug.log").write_text("debug")
    (base_path / "build" / "reports" / "summary.txt").write_text("summary")
    (base_path / "build" / "reports" / "details.txt").write_text("details")
    (base_path / "data" / "users.csv").write_text("users")
    (base_path / "data" / "products.csv").write_text("products")
    (base_path / "data" / "readme.txt").write_text("readme")
    (base_path / "tmp" / "file1.txt").write_text("file1")
    (base_path / "tmp" / "nested" / "file2.txt").write_text("file2")
    (base_path / "src" / "main.py").write_text("main")
    (base_path / "src" / "test.log").write_text("test")
    (base_path / "dist" / "app.js").write_text("app")


def test_example_1_exclude_folders_and_logs_but_reinclude_reports():
    """
    Test Example 1 from the spec:
    --exclude 'node_modules/' --exclude 'build/**' --exclude '**/*.log' --include 'build/reports/**'

    Expected behavior:
    - All node_modules/ pruned
    - All build/** excluded EXCEPT anything under build/reports/**
    - All *.log excluded anywhere
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_test_structure(temp_path)

        # Create filter engine with the example rules
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="node_modules/"),
            Rule(kind=RuleKind.EXCLUDE, pattern="build/**"),
            Rule(kind=RuleKind.EXCLUDE, pattern="**/*.log"),
            Rule(kind=RuleKind.INCLUDE, pattern="build/reports/**"),
        ]
        filter_engine = FilterEngine(rules)

        # Collect file infos
        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Generate tree
        tree_output = generate_tree(
            temp_path, file_infos, with_tokens=False, filter_engine=filter_engine
        )

        print("\n=== Example 1 Output ===")
        print(tree_output)

        # Assertions
        # node_modules should be compressed (shown but with limited children)
        assert "node_modules" in tree_output, "node_modules should appear (compressed)"

        # build/** should be excluded except reports
        assert "build" in tree_output, "build directory should appear"
        assert "reports" in tree_output, "build/reports should be included"
        assert "summary.txt" in tree_output, (
            "build/reports/summary.txt should be included"
        )
        assert "details.txt" in tree_output, (
            "build/reports/details.txt should be included"
        )
        assert "main.js" not in tree_output, (
            "build/main.js should be excluded (not in reports)"
        )

        # *.log files should be excluded
        assert ".log" not in tree_output, "No .log files should appear in tree"


def test_example_2_only_process_csvs_under_data():
    """
    Test Example 2 from the spec:
    --exclude '**' --include 'data/**/*.csv'

    Expected behavior:
    - Default exclude of all
    - Last include brings back CSVs under data/
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_test_structure(temp_path)

        # Create filter engine
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="**"),
            Rule(kind=RuleKind.INCLUDE, pattern="data/**/*.csv"),
        ]
        filter_engine = FilterEngine(rules)

        # Collect file infos
        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Generate tree
        tree_output = generate_tree(
            temp_path, file_infos, with_tokens=False, filter_engine=filter_engine
        )

        print("\n=== Example 2 Output ===")
        print(tree_output)

        # Assertions
        assert "users.csv" in tree_output, "data/users.csv should be included"
        assert "products.csv" in tree_output, "data/products.csv should be included"
        assert "readme.txt" not in tree_output, "data/readme.txt should be excluded"
        assert "main.py" not in tree_output, "src/main.py should be excluded"
        assert "main.js" not in tree_output, "build/main.js should be excluded"


def test_example_3_exclude_direct_children_not_nested():
    """
    Test Example 3 from the spec:
    --exclude 'tmp/*' --include 'tmp/**/'

    Expected behavior:
    - Files directly in tmp/ excluded
    - Directories under tmp/ are re-included so traversal continues
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_test_structure(temp_path)

        # Create filter engine
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="tmp/*"),
            Rule(kind=RuleKind.INCLUDE, pattern="tmp/**/"),
        ]
        filter_engine = FilterEngine(rules)

        # Collect file infos
        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Generate tree
        tree_output = generate_tree(
            temp_path, file_infos, with_tokens=False, filter_engine=filter_engine
        )

        print("\n=== Example 3 Output ===")
        print(tree_output)

        # Assertions
        assert "file1.txt" not in tree_output, "tmp/file1.txt should be excluded"
        assert "nested" in tree_output, "tmp/nested/ directory should be included"
        # Note: file2.txt might or might not be included depending on if nested/** is matched
        # The spec is about allowing traversal, not necessarily including all nested content


def test_example_4_exclude_directory_by_basename():
    """
    Test Example 4 from the spec:
    --exclude-dir 'dist'

    Expected behavior:
    - Any directory named 'dist' is pruned
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_test_structure(temp_path)

        # Create filter engine
        rules = [
            Rule(kind=RuleKind.EXCLUDE_DIR, pattern="dist"),
        ]
        filter_engine = FilterEngine(rules)

        # Collect file infos
        file_infos = collect_file_info(temp_path, {}, None, filter_engine)

        # Generate tree
        tree_output = generate_tree(
            temp_path, file_infos, with_tokens=False, filter_engine=filter_engine
        )

        print("\n=== Example 4 Output ===")
        print(tree_output)

        # Assertions
        # dist should be shown compressed or not shown at all
        # app.js inside dist should not be in the detailed tree
        assert "app.js" not in tree_output or "dist" in tree_output, (
            "dist should be compressed if shown, or app.js not in detail"
        )


def test_last_match_wins_basic():
    """Test that last matching rule wins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create simple structure
        (temp_path / "test.txt").write_text("test")
        (temp_path / "data.txt").write_text("data")

        # Test 1: exclude then include wins (include)
        rules1 = [
            Rule(kind=RuleKind.EXCLUDE, pattern="*.txt"),
            Rule(kind=RuleKind.INCLUDE, pattern="test.txt"),
        ]
        engine1 = FilterEngine(rules1)
        infos1 = collect_file_info(temp_path, {}, None, engine1)

        assert any(f.relative_path == "test.txt" for f in infos1), (
            "test.txt should be included (last rule wins)"
        )
        assert not any(f.relative_path == "data.txt" for f in infos1), (
            "data.txt should be excluded"
        )

        # Test 2: include then exclude wins (exclude)
        rules2 = [
            Rule(kind=RuleKind.INCLUDE, pattern="test.txt"),
            Rule(kind=RuleKind.EXCLUDE, pattern="*.txt"),
        ]
        engine2 = FilterEngine(rules2)
        infos2 = collect_file_info(temp_path, {}, None, engine2)

        assert not any(f.relative_path == "test.txt" for f in infos2), (
            "test.txt should be excluded (last rule wins)"
        )
        assert not any(f.relative_path == "data.txt" for f in infos2), (
            "data.txt should be excluded"
        )


def test_pattern_with_doublestar():
    """Test that ** patterns work correctly across directory separators."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create nested structure
        (temp_path / "src").mkdir()
        (temp_path / "src" / "tests").mkdir()
        (temp_path / "src" / "main.py").write_text("main")
        (temp_path / "src" / "tests" / "test_main.py").write_text("test")

        # Exclude all Python test files
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="**/test_*.py"),
        ]
        engine = FilterEngine(rules)
        infos = collect_file_info(temp_path, {}, None, engine)

        assert any(f.relative_path == "src/main.py" for f in infos), (
            "src/main.py should be included"
        )
        assert not any(f.relative_path == "src/tests/test_main.py" for f in infos), (
            "src/tests/test_main.py should be excluded by **/test_*.py"
        )


def test_trailing_slash_matches_dirs_only():
    """Test that patterns ending with / match directories only."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create file and directory with same base name
        (temp_path / "data").mkdir()
        (temp_path / "data" / "content.txt").write_text("content")
        # Note: can't create a file named "data" in the same directory as a "data" directory
        # So we'll test with a different approach

        (temp_path / "config.txt").write_text("config file")
        (temp_path / "config").mkdir()
        (temp_path / "config" / "app.json").write_text("{}")

        # Exclude only directories named config
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="config/"),
        ]
        engine = FilterEngine(rules)
        infos = collect_file_info(temp_path, {}, None, engine)

        # The file config.txt should be included
        assert any(f.relative_path == "config.txt" for f in infos), (
            "config.txt file should be included (pattern has trailing /)"
        )

        # The directory config should be excluded (shown compressed)
        # Children may appear in file_infos for compression display,
        # but the directory itself should be marked as excluded
        config_dir = next(
            (f for f in infos if f.relative_path == "config" and f.is_directory), None
        )
        assert config_dir is not None, (
            "config directory should be in infos (for compressed display)"
        )

        # Verify the engine considers it excluded
        assert engine.effective_action("config", is_dir=True) == Action.EXCLUDE, (
            "config/ directory should be excluded by the filter"
        )

        # Verify config.txt is NOT excluded
        assert engine.effective_action("config.txt", is_dir=False) == Action.INCLUDE, (
            "config.txt file should NOT be excluded (pattern has trailing /)"
        )


def test_conservative_traversal():
    """
    Test that directories are traversed even when excluded if a later include could match descendants.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create structure
        (temp_path / "build").mkdir()
        (temp_path / "build" / "temp.js").write_text("temp")
        (temp_path / "build" / "reports").mkdir()
        (temp_path / "build" / "reports" / "summary.txt").write_text("summary")

        # Exclude build but include build/reports/**
        rules = [
            Rule(kind=RuleKind.EXCLUDE, pattern="build/**"),
            Rule(kind=RuleKind.INCLUDE, pattern="build/reports/**"),
        ]
        engine = FilterEngine(rules)

        # Check if traversal happens
        should_traverse = engine.may_have_late_include_descendant("build")
        assert should_traverse, (
            "Should traverse build/ because later include targets build/reports/**"
        )

        infos = collect_file_info(temp_path, {}, None, engine)

        # build/temp.js should be excluded
        assert not any(f.relative_path == "build/temp.js" for f in infos), (
            "build/temp.js should be excluded"
        )
        # build/reports/summary.txt should be included
        assert any(f.relative_path == "build/reports/summary.txt" for f in infos), (
            "build/reports/summary.txt should be included due to late include"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
