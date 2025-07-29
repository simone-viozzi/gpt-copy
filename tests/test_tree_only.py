# File: tests/test_tree_only.py

import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

from gpt_copy.gpt_copy import main


def test_tree_only_flag():
    """Test that --tree-only outputs only the folder structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        (temp_path / "file1.py").write_text("print('hello')")
        (temp_path / "file2.md").write_text("# Header")
        subdir = temp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content")
        
        runner = CliRunner()
        
        # Test tree-only output
        result = runner.invoke(main, [str(temp_path), "--tree-only"])
        assert result.exit_code == 0
        
        # Should contain tree structure
        assert temp_path.name in result.output
        assert "├── file1.py" in result.output or "file1.py" in result.output
        assert "├── file2.md" in result.output or "file2.md" in result.output
        assert "subdir" in result.output
        
        # Should NOT contain file contents
        assert "print('hello')" not in result.output
        assert "# Header" not in result.output
        assert "content" not in result.output
        
        # Should NOT contain markdown headers
        assert "# Folder Structure" not in result.output
        assert "## File:" not in result.output


def test_tree_only_vs_normal_output():
    """Test that tree-only output is different from normal output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test file
        (temp_path / "test.py").write_text("print('test')")
        
        runner = CliRunner()
        
        # Normal output
        normal_result = runner.invoke(main, [str(temp_path)])
        assert normal_result.exit_code == 0
        
        # Tree-only output
        tree_result = runner.invoke(main, [str(temp_path), "--tree-only"])
        assert tree_result.exit_code == 0
        
        # Tree-only should be shorter
        assert len(tree_result.output) < len(normal_result.output)
        
        # Normal output should contain file contents and markdown
        assert "print('test')" in normal_result.output
        assert "# Folder Structure" in normal_result.output
        assert "## File:" in normal_result.output
        
        # Tree-only should not contain file contents or markdown headers
        assert "print('test')" not in tree_result.output
        assert "# Folder Structure" not in tree_result.output
        assert "## File:" not in tree_result.output


def test_tree_only_with_output_file():
    """Test that --tree-only works with output file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_file = temp_path / "output.txt"
        
        # Create test files
        (temp_path / "test.py").write_text("print('hello')")
        
        runner = CliRunner()
        result = runner.invoke(main, [str(temp_path), "--tree-only", "-o", str(output_file)])
        assert result.exit_code == 0
        
        # Check that output file was created and contains only tree
        assert output_file.exists()
        content = output_file.read_text()
        
        # Should contain tree structure
        assert temp_path.name in content
        assert "test.py" in content
        
        # Should NOT contain file contents or markdown headers
        assert "print('hello')" not in content
        assert "# Folder Structure" not in content
        assert "## File:" not in content