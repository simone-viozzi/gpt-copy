#!/usr/bin/env python3
"""
Integration tests for gpt-copy tokens functionality.
Tests the CLI interface and integration with existing functionality.
"""

import tempfile
import subprocess
import sys
from pathlib import Path
import os


def run_gpt_copy_command(args, cwd=None):
    """Run gpt-copy command and return output."""
    # Create a wrapper script to run gpt-copy
    wrapper_script = f"""
import sys
sys.path.insert(0, "{Path(__file__).parent.parent / "src"}")
from gpt_copy.gpt_copy import main

if __name__ == "__main__":
    main()
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper_script)
        wrapper_path = f.name

    try:
        cmd = [sys.executable, wrapper_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return result.returncode, result.stdout, result.stderr
    finally:
        os.unlink(wrapper_path)


def test_tokens_option_basic():
    """Test basic --tokens functionality."""
    print("Testing basic --tokens functionality...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "file1.py").write_text("print('hello world')")
        (temp_path / "file2.js").write_text("console.log('test');")

        # Run gpt-copy with --tokens
        returncode, stdout, stderr = run_gpt_copy_command([str(temp_path), "--tokens"])

        assert returncode == 0, f"Command failed with stderr: {stderr}"
        assert "tokens)" in stdout, "Output should contain token counts"
        assert "file1.py" in stdout, "Output should contain file1.py"
        assert "file2.js" in stdout, "Output should contain file2.js"

        print("✓ Basic --tokens functionality works")


def test_tokens_with_top_n():
    """Test --tokens with --top-n functionality."""
    print("Testing --tokens with --top-n...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files with different lengths
        (temp_path / "small.py").write_text("x=1")
        (temp_path / "medium.py").write_text("print('hello world')")
        (temp_path / "large.py").write_text(
            "# This is a long comment\nprint('hello world')\n# Another comment"
        )

        # Run gpt-copy with --tokens --top-n 2
        returncode, stdout, stderr = run_gpt_copy_command(
            [str(temp_path), "--tokens", "--top-n", "2"]
        )

        assert returncode == 0, f"Command failed with stderr: {stderr}"
        assert "Showing top 2 files" in stdout, "Should show top-n message"

        # The largest file should be included
        assert "large.py" in stdout, "Largest file should be included"

        print("✓ --tokens with --top-n works")


def test_tokens_with_include_filter():
    """Test --tokens with file filtering."""
    print("Testing --tokens with include filters...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "script.py").write_text("print('python script')")
        (temp_path / "app.js").write_text("console.log('javascript');")
        (temp_path / "readme.txt").write_text("This is documentation")

        # Run gpt-copy with --tokens and Python filter
        returncode, stdout, stderr = run_gpt_copy_command(
            [str(temp_path), "--tokens", "--include", "*.py"]
        )

        assert returncode == 0, f"Command failed with stderr: {stderr}"
        assert "script.py" in stdout, "Python file should be included"
        assert "app.js" not in stdout, "JavaScript file should be excluded"
        assert "readme.txt" not in stdout, "Text file should be excluded"

        print("✓ --tokens with include filters works")


def test_tokens_help_option():
    """Test that help shows the new options."""
    print("Testing help output includes new options...")

    returncode, stdout, stderr = run_gpt_copy_command(["--help"])

    # Help should work (even without a directory argument)
    assert "--tokens" in stdout, "Help should show --tokens option"
    assert "--top-n" in stdout, "Help should show --top-n option"
    assert "Display token counts" in stdout, "Help should describe --tokens"
    assert "top N files by token count" in stdout, "Help should describe --top-n"

    print("✓ Help output includes new options")


def test_regular_functionality_still_works():
    """Test that existing functionality is not broken."""
    print("Testing that regular functionality still works...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test file
        (temp_path / "test.py").write_text("print('test')")

        # Test regular tree-only functionality
        returncode, stdout, stderr = run_gpt_copy_command(
            [str(temp_path), "--tree-only"]
        )

        assert returncode == 0, f"Command failed with stderr: {stderr}"
        assert "test.py" in stdout, "File should appear in tree"
        assert "tokens)" not in stdout, "Should not show token counts in regular mode"

        print("✓ Regular functionality still works")


def test_tokens_without_top_n():
    """Test that --top-n without --tokens is ignored."""
    print("Testing --top-n without --tokens is ignored...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test file
        (temp_path / "test.py").write_text("print('test')")

        # Use --top-n without --tokens
        returncode, stdout, stderr = run_gpt_copy_command(
            [str(temp_path), "--top-n", "1", "--tree-only"]
        )

        assert returncode == 0, f"Command failed with stderr: {stderr}"
        assert "test.py" in stdout, "File should appear normally"
        assert "tokens)" not in stdout, "Should not show token counts"
        assert "Showing top" not in stdout, "Should not show top-n message"

        print("✓ --top-n without --tokens is ignored correctly")


def run_all_cli_tests():
    """Run all CLI tests."""
    print("Running CLI integration tests for token functionality...\n")

    try:
        test_tokens_option_basic()
        test_tokens_with_top_n()
        test_tokens_with_include_filter()
        test_tokens_help_option()
        test_regular_functionality_still_works()
        test_tokens_without_top_n()

        print("\n" + "=" * 60)
        print("✅ All CLI tests passed successfully!")
        print("Token functionality is properly integrated with CLI.")

    except Exception as e:
        print(f"\n❌ CLI test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    run_all_cli_tests()
