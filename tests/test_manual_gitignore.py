import tempfile
import pytest
from pathlib import Path
from click.testing import CliRunner
import pickle
from collections.abc import Generator

from gpt_copy.gpt_copy import (
    infer_language,  # updated import
    generate_tree,
    collect_gitignore_specs,
    collect_files_content,
    collect_file_info,
    main,
    is_ignored,
)
from gpt_copy.filter import FilterEngine


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory with test files and a .gitignore."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "file.py").write_text("print('Hello, world!')", encoding="utf-8")
        (root / "file.txt").write_text("This is a text file.", encoding="utf-8")
        (root / "subdir").mkdir()
        (root / "subdir/script.js").write_text(
            "console.log('Hello');", encoding="utf-8"
        )
        (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00")
        (root / "document.pdf").write_bytes(
            b"%PDF-1.4\n%\xc3\xa2\xc3\xa3\xc3\x8f\xc3\x93\n1 0 obj\n<<\n/Type /Catalog\n"
        )

        data = {"key": "value", "number": 42}
        with open(root / "document.pkl", "wb") as f:
            pickle.dump(data, f)

        # Create a .gitignore file
        (root / ".gitignore").write_text(
            """subdir/
            *.png
            *.pdf
            """.replace(" ", ""),
            encoding="utf-8",
        )

        yield root


def test_infer_language():
    """Test language inference from filename or extension."""
    # Special-case for Dockerfile
    assert infer_language(Path("Dockerfile")) == "docker"
    # Minimal mapping for common extensions
    assert infer_language(Path("file.py")) == "python"
    assert infer_language(Path("file.js")) == "javascript"
    # Unknown extension should return an empty string
    assert infer_language(Path("file.unknown")) == ""


def test_generate_tree(temp_directory: Path):
    """Ensure directory tree generation works correctly using .gitignore rules."""
    gitignore_specs = collect_gitignore_specs(temp_directory)
    # Create empty filter engine (no CLI rules, so everything is included)
    filter_engine = FilterEngine([])
    file_infos = collect_file_info(
        temp_directory, gitignore_specs, tracked_files=None, filter_engine=filter_engine
    )
    tree = generate_tree(temp_directory, file_infos, with_tokens=False)

    assert "file.py" in tree
    # Since the .gitignore in this fixture ignores subdir/, it should NOT appear in the tree.
    assert "subdir" not in tree
    assert "file.txt" in tree
    assert "subdir/script.js" not in tree
    assert "image.png" not in tree
    assert "document.pdf" not in tree
    assert "document.pkl" in tree


def test_collect_gitignore_specs(temp_directory: Path):
    """Ensure gitignore rules are correctly collected and applied."""
    specs = collect_gitignore_specs(temp_directory)
    assert specs is not None
    assert any(spec.match_file("document.pdf") for spec in specs.values())
    assert any(spec.match_file("subdir/script.js") for spec in specs.values())
    assert any(spec.match_file("image.png") for spec in specs.values())


def test_is_ignored(temp_directory: Path):
    """Ensure files are correctly ignored using .gitignore logic."""
    gitignore_specs = collect_gitignore_specs(temp_directory)
    temp_directory = Path(temp_directory)

    assert is_ignored(temp_directory / "document.pdf", gitignore_specs, temp_directory)
    assert is_ignored(
        temp_directory / "subdir/script.js", gitignore_specs, temp_directory
    )
    assert is_ignored(temp_directory / "image.png", gitignore_specs, temp_directory)
    assert not is_ignored(temp_directory / "file.py", gitignore_specs, temp_directory)


def test_collect_files_content(temp_directory: Path):
    """Ensure files are correctly collected and recognized."""
    gitignore_specs = collect_gitignore_specs(temp_directory)
    # Create empty filter engine
    filter_engine = FilterEngine([])
    files, unrecognized = collect_files_content(
        temp_directory, gitignore_specs, None, None, filter_engine
    )

    assert len(files) > 0
    # Now, since we use infer_language, recognized files (like file.py) will be wrapped with a language hint.
    assert any("python" in f for f in files)
    # Binary files (like document.pkl) should be listed as unrecognized.
    assert "document.pkl" in unrecognized


def test_cli(temp_directory: Path):
    """Test CLI execution with Click (using manual .gitignore parsing)."""
    runner = CliRunner()
    result = runner.invoke(main, [temp_directory.as_posix()])
    assert result.exit_code == 0
    assert "Folder Structure" in result.output
    assert "file.py" in result.output
    assert "file.txt" in result.output
