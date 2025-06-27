"""Test that line numbers are enabled by default."""

from pathlib import Path

from click.testing import CliRunner
from gpt_copy.gpt_copy import main


def test_line_numbers_enabled_by_default(tmp_path: Path):
    """Test that line numbers are enabled by default without -n flag."""
    # Create a test file with multiple lines
    test_file = tmp_path / "test.txt"
    test_file.write_text("line one\nline two\nline three\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [tmp_path.as_posix()])
    
    assert result.exit_code == 0
    # Check that line numbers are present in the output
    assert "1: line one" in result.output
    assert "2: line two" in result.output
    assert "3: line three" in result.output


def test_no_number_flag_disables_line_numbers(tmp_path: Path):
    """Test that --no-number flag disables line numbers."""
    # Create a test file with multiple lines
    test_file = tmp_path / "test.txt"
    test_file.write_text("line one\nline two\nline three\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, [tmp_path.as_posix(), "--no-number"])
    
    assert result.exit_code == 0
    # Check that line numbers are NOT present in the output
    assert "1: line one" not in result.output
    assert "2: line two" not in result.output
    assert "3: line three" not in result.output
    # But the content should still be there
    assert "line one" in result.output
    assert "line two" in result.output
    assert "line three" in result.output