import tempfile
import pytest
from pathlib import Path
from click.testing import CliRunner
from concatenate_files import (
    get_language_for_extension,
    generate_tree,
    collect_gitignore_specs,
    collect_files_content,
    main,
)


@pytest.fixture
def temp_directory():
    """Create a temporary directory with test files."""
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

        (root / "document.pkl").write_bytes(
            b"%PDF-1.4\n%\xc3\xa2\xc3\xa3\xc3\x8f\xc3\x93\n1 0 obj\n<<\n/Type /Catalog\n"
        )

        # Create a .gitignore file
        (root / ".gitignore").write_text(
            "*.txt\nsubdir/\n*.png\n*.pdf", encoding="utf-8"
        )

        yield temp_dir  # Provide the temp directory path


def test_get_language_for_extension():
    """Test file extension to language mapping."""
    assert get_language_for_extension(".py") == "python"
    assert get_language_for_extension(".js") == "javascript"
    assert get_language_for_extension(".unknown") is None


def test_generate_tree(temp_directory):
    """Ensure directory tree generation works correctly."""
    gitignore_specs = collect_gitignore_specs(temp_directory)
    tree = generate_tree(temp_directory, gitignore_specs)
    assert "file.py" in tree
    assert "subdir" in tree
    assert "file.txt" not in tree  # Should be ignored by .gitignore


def test_collect_gitignore_specs(temp_directory):
    """Ensure gitignore rules are correctly collected and applied."""
    specs = collect_gitignore_specs(temp_directory)
    assert specs is not None
    assert any(spec.match_file("file.txt") for spec in specs.values())  # Should be ignored
    assert any(spec.match_file("subdir/script.js") for spec in specs.values())  # Should be ignored


def test_collect_files_content(temp_directory):
    """Ensure files are correctly collected and recognized."""
    gitignore_specs = collect_gitignore_specs(temp_directory)
    files, unrecognized = collect_files_content(temp_directory, gitignore_specs, None)

    assert len(files) > 0  # We should have some recognized files
    assert any("python" in f for f in files)  # Python file should be there
    assert "document.pkl" in unrecognized  # Unrecognized file should be listed


def test_cli(temp_directory):
    """Test CLI execution with Click."""
    runner = CliRunner()
    result = runner.invoke(main, [temp_directory])
    assert result.exit_code == 0
    assert "Folder Structure" in result.output
    assert "file.py" in result.output
    assert "file.txt" not in result.output  # .gitignore should exclude it
