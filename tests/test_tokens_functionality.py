#!/usr/bin/env python3
"""Tests for token counting functionality in gpt-copy."""

import tempfile
import pytest
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gpt_copy.gpt_copy import (
    count_tokens_safe,
    collect_file_info_with_tokens,
    generate_tree_with_tokens,
    get_ignore_settings,
    FileInfo
)


class TestTokensCounting:
    """Test token counting functionality."""
    
    def test_count_tokens_safe_simple(self):
        """Test basic token counting."""
        # Test simple cases
        assert count_tokens_safe("Hello world") > 0
        assert count_tokens_safe("") == 1  # Minimum of 1 token
        
        # Test that more text gives more tokens
        short_text = "Hello"
        long_text = "Hello world this is a much longer piece of text that should have more tokens"
        assert count_tokens_safe(long_text) > count_tokens_safe(short_text)
    
    def test_collect_file_info_with_tokens(self):
        """Test collecting file information with token counts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "short.py").write_text("print('hi')")
            (temp_path / "long.py").write_text("# This is a much longer file with more content\nprint('hello world')\n# More comments")
            (temp_path / "empty.txt").write_text("")
            
            # Get ignore settings
            gitignore_specs, tracked_files = get_ignore_settings(temp_path, force=True)
            
            # Collect file info
            file_infos = collect_file_info_with_tokens(
                temp_path,
                gitignore_specs,
                tracked_files,
                include_patterns=None,
                exclude_patterns=None,
            )
            
            # Check results
            assert len(file_infos) == 3
            
            # Find specific files
            short_file = next(f for f in file_infos if f.relative_path == "short.py")
            long_file = next(f for f in file_infos if f.relative_path == "long.py")
            empty_file = next(f for f in file_infos if f.relative_path == "empty.txt")
            
            # Verify token counts make sense
            assert short_file.token_count > 0
            assert long_file.token_count > short_file.token_count
            assert empty_file.token_count == 1  # Minimum 1 token
    
    def test_generate_tree_with_tokens(self):
        """Test generating tree structure with token counts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "file1.py").write_text("print('test1')")
            (temp_path / "file2.py").write_text("print('test2 with more content')")
            
            # Create file infos
            file_infos = [
                FileInfo(temp_path / "file1.py", "file1.py", 3, False),
                FileInfo(temp_path / "file2.py", "file2.py", 7, False),
            ]
            
            # Generate tree
            tree_output = generate_tree_with_tokens(
                temp_path,
                file_infos,
                {},  # gitignore_specs
                None,  # tracked_files
                None,  # exclude_patterns
                None,  # top_n
            )
            
            # Check output contains token counts
            assert "3 tokens" in tree_output
            assert "7 tokens" in tree_output
            assert "file1.py" in tree_output
            assert "file2.py" in tree_output
    
    def test_generate_tree_with_tokens_top_n(self):
        """Test generating tree with top-N filtering and correct ordering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create file infos with different token counts (in random order)
            file_infos = [
                FileInfo(temp_path / "small.py", "small.py", 2, False),
                FileInfo(temp_path / "medium.py", "medium.py", 5, False),
                FileInfo(temp_path / "large.py", "large.py", 10, False),
                FileInfo(temp_path / "subdir/huge.py", "subdir/huge.py", 15, False),
            ]
            
            # Generate tree with top-3
            tree_output = generate_tree_with_tokens(
                temp_path,
                file_infos,
                {},  # gitignore_specs
                None,  # tracked_files
                None,  # exclude_patterns
                3,  # top_n
            )
            
            # Check only top 3 files are included
            assert "huge.py" in tree_output  # 15 tokens - should be included (in subdir)
            assert "large.py" in tree_output  # 10 tokens - should be included
            assert "medium.py" in tree_output  # 5 tokens - should be included
            assert "small.py" not in tree_output  # 2 tokens - should be excluded
            assert "Showing top 3 files" in tree_output
            
            # Check that files are in correct order by token count within the tree structure
            lines = tree_output.split('\n')
            
            # With the new tree structure, we should see:
            # - subdir/ directory listed first (highest tokens: 15)
            # - huge.py (15 tokens) inside subdir
            # - large.py (10 tokens) at root level
            # - medium.py (5 tokens) at root level
            assert "subdir/ (15 tokens)" in tree_output
            assert "huge.py (15 tokens)" in tree_output
            assert "large.py (10 tokens)" in tree_output
            assert "medium.py (5 tokens)" in tree_output
    
    def test_file_filtering_with_tokens(self):
        """Test that file filtering works with token counting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "test.py").write_text("print('python')")
            (temp_path / "test.js").write_text("console.log('javascript')")
            (temp_path / "readme.txt").write_text("This is a readme file")
            
            # Get ignore settings
            gitignore_specs, tracked_files = get_ignore_settings(temp_path, force=True)
            
            # Collect only Python files
            file_infos = collect_file_info_with_tokens(
                temp_path,
                gitignore_specs,
                tracked_files,
                include_patterns=["*.py"],
                exclude_patterns=None,
            )
            
            # Should only have the Python file
            assert len(file_infos) == 1
            assert file_infos[0].relative_path == "test.py"
            assert file_infos[0].token_count > 0


if __name__ == "__main__":
    pytest.main([__file__])