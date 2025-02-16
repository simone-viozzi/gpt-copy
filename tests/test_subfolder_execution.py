from pathlib import Path

import pygit2
from click.testing import CliRunner
from gpt_copy.gpt_copy import main


def test_subfolder_non_git(tmp_path: Path):
    """
    Test that when running the script from a subfolder of a non-git directory,
    only files within that subfolder are processed.
    """
    # Create a temporary non-git directory structure.
    root = tmp_path / "non_git_repo"
    root.mkdir()
    (root / "file1.txt").write_text("Root file", encoding="utf-8")

    subfolder = root / "subfolder"
    subfolder.mkdir()
    (subfolder / "file2.txt").write_text("Subfolder file", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [subfolder.as_posix()])
    assert result.exit_code == 0, result.output
    # Verify that the folder tree and file content reflect only the subfolder.
    assert "file2.txt" in result.output
    assert "file1.txt" not in result.output


def test_subfolder_git(tmp_path: Path):
    """
    Test that when running the script from a subfolder of a Git repository,
    the repository is correctly discovered and only tracked files within that subfolder are processed.
    """
    # Create a temporary Git repository.
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()
    repo = pygit2.init_repository(repo_dir.as_posix(), bare=False)

    # Create a file in the repository root.
    (repo_dir / "file1.txt").write_text("Root git file", encoding="utf-8")

    # Create a subfolder with a file.
    subfolder = repo_dir / "subfolder"
    subfolder.mkdir()
    (subfolder / "file2.txt").write_text("Subfolder git file", encoding="utf-8")

    # Stage and commit all files.
    repo.index.add_all()
    repo.index.write()
    author = pygit2.Signature("Tester", "tester@example.com")
    committer = pygit2.Signature("Tester", "tester@example.com")
    repo.create_commit(
        "HEAD", author, committer, "Initial commit", repo.index.write_tree(), []
    )

    runner = CliRunner()
    result = runner.invoke(main, [subfolder.as_posix()])
    assert result.exit_code == 0, result.output
    # Check that only the file inside the subfolder is included.
    assert "file2.txt" in result.output
    # The root file should not appear because it is outside the provided subfolder.
    assert "file1.txt" not in result.output
