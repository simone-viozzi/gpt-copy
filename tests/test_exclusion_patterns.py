#!/usr/bin/env python3
"""Test exclusion pattern behavior to ensure patterns are relative to original working directory."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from gpt_copy.gpt_copy import main


class TestExclusionPatterns:
    """Test exclusion patterns work correctly relative to the original working directory."""

    def test_exclusion_pattern_relative_to_cwd(self):
        """Test that exclusion patterns are interpreted relative to the original working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create directory structure: temp_dir/test/dropbox/file.txt
            test_dir = temp_path / "test"
            dropbox_dir = test_dir / "dropbox"
            dropbox_dir.mkdir(parents=True)
            
            # Create files
            (test_dir / "should_be_included.txt").write_text("content")
            (dropbox_dir / "should_be_excluded.txt").write_text("dropbox content")
            
            runner = CliRunner()
            
            # Change to temp_dir and run gpt-copy on "test" subdirectory with exclusion "test/dropbox/*"
            with runner.isolated_filesystem(temp_dir=temp_dir):
                os.chdir(temp_dir)
                
                # Test case 1: "test/dropbox/*" pattern should exclude files in dropbox
                result = runner.invoke(main, ["test", "-e", "test/dropbox/*", "--tree-only"])
                assert result.exit_code == 0
                
                # dropbox.txt should be excluded
                assert "should_be_excluded.txt" not in result.output
                # Other files should be included
                assert "should_be_included.txt" in result.output
                # The dropbox directory might still appear but should be compressed/empty

    def test_exclusion_pattern_directory_itself(self):
        """Test that exclusion patterns can exclude directories themselves.""" 
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create directory structure: temp_dir/test/dropbox/file.txt
            test_dir = temp_path / "test"
            dropbox_dir = test_dir / "dropbox"
            dropbox_dir.mkdir(parents=True)
            
            # Create files
            (test_dir / "should_be_included.txt").write_text("content")
            (dropbox_dir / "should_be_excluded.txt").write_text("dropbox content")
            
            runner = CliRunner()
            
            # Change to temp_dir and run gpt-copy on "test" subdirectory with exclusion "test/dropbox"
            with runner.isolated_filesystem(temp_dir=temp_dir):
                os.chdir(temp_dir)
                
                # Test case 3: "test/dropbox" pattern should exclude the dropbox directory
                result = runner.invoke(main, ["test", "-e", "test/dropbox", "--tree-only"])
                assert result.exit_code == 0
                
                # dropbox directory should show as compressed (with [...])  
                # since it's excluded but contains files
                assert "dropbox" in result.output
                assert "[...]" in result.output or "should_be_excluded.txt" not in result.output

    def test_exclusion_pattern_without_prefix(self):
        """Test that patterns without the directory prefix work relative to scan directory.""" 
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create directory structure: temp_dir/test/dropbox/file.txt
            test_dir = temp_path / "test"
            dropbox_dir = test_dir / "dropbox"
            dropbox_dir.mkdir(parents=True)
            
            # Create files
            (test_dir / "should_be_included.txt").write_text("content")
            (dropbox_dir / "should_be_excluded.txt").write_text("dropbox content")
            
            runner = CliRunner()
            
            # Change to temp_dir and run gpt-copy on "test" subdirectory with exclusion "dropbox/*"
            with runner.isolated_filesystem(temp_dir=temp_dir):
                os.chdir(temp_dir)
                
                # Test case 2: "dropbox/*" should NOT exclude since there's no dropbox in cwd
                result = runner.invoke(main, ["test", "-e", "dropbox/*", "--tree-only"])
                assert result.exit_code == 0
                
                # Files should still be included since dropbox/* doesn't match anything from cwd
                assert "should_be_excluded.txt" in result.output
                assert "should_be_included.txt" in result.output