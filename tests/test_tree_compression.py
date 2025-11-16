from pathlib import Path
from gpt_copy.gpt_copy import generate_tree, collect_file_info
from gpt_copy.filter import FilterEngine, Rule, RuleKind


def test_generate_tree_excluded(tmp_path: Path):
    # Create a temporary directory structure.
    root = tmp_path / "root"
    root.mkdir()

    # Create a file in the root.
    (root / "file1.txt").write_text("Root file", encoding="utf-8")

    # Create an included directory (should display fully).
    include_dir = root / "include_dir"
    include_dir.mkdir()
    (include_dir / "file2.txt").write_text("Include file", encoding="utf-8")

    # Create an excluded directory (should be compressed).
    exclude_dir = root / "exclude_dir"
    exclude_dir.mkdir()
    # Add four files to the excluded directory to trigger compression (max_items is 3)
    for i in range(1, 5):
        (exclude_dir / f"file{i + 2}.txt").write_text(
            f"Exclude file {i}", encoding="utf-8"
        )

    # For testing purposes, assume no gitignored files.
    gitignore_specs = {}
    tracked_files = None
    
    # Create filter engine with exclude pattern for exclude_dir
    rules = [Rule(kind=RuleKind.EXCLUDE, pattern="exclude_dir")]
    filter_engine = FilterEngine(rules)

    # Collect file infos
    file_infos = collect_file_info(
        root, gitignore_specs, tracked_files, filter_engine=filter_engine
    )

    # Generate the tree using the new compressed view for excluded directories.
    tree_output = generate_tree(
        root, file_infos, with_tokens=False, filter_engine=filter_engine
    )

    # Debug print (optional)
    print(tree_output)

    # Verify that the excluded directory is shown in compressed form.
    assert "exclude_dir" in tree_output
    # The compressed view should show at most 3 children of the excluded directory.
    assert "file3.txt" in tree_output
    assert "file4.txt" in tree_output
    assert "file5.txt" in tree_output
    # There should be an ellipsis indicating additional files.
    assert "[...]" in tree_output
    # Ensure that the fourth child (file6.txt) is not shown.
    assert "file6.txt" not in tree_output

    # Also verify that the included directory is fully expanded.
    assert "include_dir" in tree_output
    assert "file2.txt" in tree_output
