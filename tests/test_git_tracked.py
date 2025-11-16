import tempfile
import pytest
from pathlib import Path
import pygit2
from click.testing import CliRunner
from gpt_copy.gpt_copy import (
    get_tracked_files,
    is_ignored,
    main,
    generate_tree,
    collect_files_content,
    collect_file_info,
)
from gpt_copy.filter import FilterEngine
from collections.abc import Generator


@pytest.fixture
def git_repo() -> Generator[Path, None, None]:
    """Create a temporary Git repository with some tracked and untracked files, and a .gitignore."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        repo = pygit2.init_repository(root.as_posix(), bare=False)

        # Create tracked files
        (root / "file.py").write_text("print('Hello, world!')", encoding="utf-8")
        (root / "file.txt").write_text("This is a text file.", encoding="utf-8")

        # Create a .gitignore file
        (root / ".gitignore").write_text(
            """*.log
            ignored_folder/
            """.replace(" ", ""),
            encoding="utf-8",
        )

        (root / "tracked_folder").mkdir()
        (root / "tracked_folder/tracked_file.py").write_text(
            "print('This is a tracked file in a folder.')", encoding="utf-8"
        )

        # Stage and commit tracked files
        repo.index.add_all()
        repo.index.write()
        author = pygit2.Signature("Test User", "test@example.com")
        committer = pygit2.Signature("Test User", "test@example.com")
        repo.create_commit(
            "HEAD", author, committer, "Initial commit", repo.index.write_tree(), []
        )

        # Create files that should NOT be tracked
        (root / "untracked.log").write_text("This file is untracked.", encoding="utf-8")
        (root / "ignored.log").write_text(
            "This file is ignored by .gitignore.", encoding="utf-8"
        )
        (root / "ignored_folder").mkdir()
        (root / "ignored_folder/hidden.txt").write_text(
            "This file is ignored.", encoding="utf-8"
        )

        yield root


def test_get_tracked_files(git_repo: Path):
    """Ensure tracked files are correctly retrieved from Git."""
    repo = pygit2.Repository(git_repo.as_posix())
    tracked_files = get_tracked_files(repo)

    assert "file.py" in tracked_files
    assert "file.txt" in tracked_files
    assert ".gitignore" in tracked_files  # The .gitignore itself is tracked
    assert "untracked.log" not in tracked_files  # This file should remain untracked
    assert "ignored.log" not in tracked_files  # This file is ignored by .gitignore
    assert "ignored_folder/hidden.txt" not in tracked_files  # Ignored folder
    assert "tracked_folder/tracked_file.py" in tracked_files


def test_is_ignored_git(git_repo: Path):
    """Ensure is_ignored() correctly differentiates between tracked, untracked, and ignored files."""
    repo = pygit2.Repository(git_repo.as_posix())
    tracked_files = get_tracked_files(repo)

    assert not is_ignored(git_repo / "file.py", {}, git_repo, tracked_files)
    assert not is_ignored(git_repo / "file.txt", {}, git_repo, tracked_files)
    assert is_ignored(
        git_repo / "untracked.log", {}, git_repo, tracked_files
    )  # Not tracked
    assert is_ignored(
        git_repo / "ignored.log", {}, git_repo, tracked_files
    )  # Ignored by .gitignore
    assert is_ignored(
        git_repo / "ignored_folder/hidden.txt", {}, git_repo, tracked_files
    )  # Ignored folder


def test_generate_tree_git(git_repo: Path):
    """Ensure directory tree only includes tracked files."""
    repo = pygit2.Repository(git_repo.as_posix())
    tracked_files = get_tracked_files(repo)

    filter_engine = FilterEngine([])
    file_infos = collect_file_info(git_repo, {}, tracked_files, filter_engine)
    tree = generate_tree(
        git_repo, file_infos, with_tokens=False, filter_engine=filter_engine
    )

    assert "file.py" in tree
    assert "file.txt" in tree
    assert ".gitignore" in tree
    assert "untracked.log" not in tree  # Should be ignored
    assert "ignored.log" not in tree  # Should be ignored
    assert "ignored_folder" not in tree  # Should be ignored
    # Instead of expecting a full path string, verify that both folder and file names appear.
    assert "tracked_folder" in tree
    assert "tracked_file.py" in tree


def test_collect_files_content_git(git_repo: Path):
    """Ensure content collection respects Git-tracked files and ignores untracked/ignored ones."""
    repo = pygit2.Repository(git_repo.as_posix())
    tracked_files = get_tracked_files(repo)

    filter_engine = FilterEngine([])
    files, unrecognized = collect_files_content(
        git_repo, {}, None, tracked_files, filter_engine
    )

    assert len(files) > 0
    assert any("file.py" in f for f in files)
    assert "untracked.log" not in str(files)  # Not tracked, should be ignored
    assert "ignored.log" not in str(files)  # Should be ignored
    assert "ignored_folder/hidden.txt" not in str(files)  # Should be ignored
    assert any("tracked_folder/tracked_file.py" in f for f in files)


def test_cli_git(git_repo: Path):
    """Test CLI execution with Click (using Git tracking)."""
    runner = CliRunner()
    result = runner.invoke(main, [git_repo.as_posix()])
    assert result.exit_code == 0

    # Extract the folder structure tree from the CLI output.
    # The tree is printed between the first pair of triple backticks.
    tree_section = ""
    parts = result.output.split("```")
    if len(parts) > 1:
        tree_section = parts[1]

    # Validate the tree portion.
    assert "file.py" in tree_section
    assert "file.txt" in tree_section
    assert ".gitignore" in tree_section
    assert "ignored.log" not in tree_section
    # Check that the ignored folder is not listed in the tree.
    assert "ignored_folder" not in tree_section
    # Verify that tracked_folder and its file appear.
    assert "tracked_folder" in tree_section
    assert "tracked_file.py" in tree_section
