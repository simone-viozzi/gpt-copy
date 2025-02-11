import tempfile
import pytest
from pathlib import Path
import pygit2
from click.testing import CliRunner
from src.concatenate_files.concatenate_files import (
    get_tracked_files,
    is_ignored,
    main,
    generate_tree,
    collect_files_content,
)
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

    tree = generate_tree(git_repo, {}, tracked_files)

    assert "file.py" in tree
    assert "file.txt" in tree
    assert ".gitignore" in tree
    assert "untracked.log" not in tree  # Should be ignored
    assert "ignored.log" not in tree  # Should be ignored
    assert "ignored_folder" not in tree  # Should be ignored


def test_collect_files_content_git(git_repo: Path):
    """Ensure content collection respects Git-tracked files and ignores untracked/ignored ones."""
    repo = pygit2.Repository(git_repo.as_posix())
    tracked_files = get_tracked_files(repo)

    files, unrecognized = collect_files_content(git_repo, {}, None, tracked_files)

    assert len(files) > 0
    assert any("file.py" in f for f in files)
    assert "untracked.log" not in str(files)  # Not tracked, should be ignored
    assert "ignored.log" not in str(files)  # Should be ignored
    assert "ignored_folder/hidden.txt" not in str(files)  # Should be ignored


def test_cli_git(git_repo: Path):
    """Test CLI execution with Click (using Git tracking)."""
    runner = CliRunner()
    result = runner.invoke(main, [git_repo.as_posix()])
    assert result.exit_code == 0
    assert "Folder Structure" in result.output
    assert "file.py" in result.output
    assert "file.txt" in result.output
    assert ".gitignore" in result.output
    assert "untracked.log" not in result.output  # Should be ignored
    assert "ignored.log" not in result.output  # Should be ignored
    assert "ignored_folder" not in result.output  # Should be ignored
