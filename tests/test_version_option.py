#!/usr/bin/env python3

import subprocess
import importlib.metadata


def test_version_option_via_console_script():
    """Test that --version option works when called via the console script."""
    # Get the expected version from package metadata
    expected_version = importlib.metadata.version("gpt_copy")

    # Test the --version option via console script
    result = subprocess.run(["gpt-copy", "--version"], capture_output=True, text=True)

    # Verify exit code is 0
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"

    # Verify the output contains the version
    expected_output = f"gpt-copy, version {expected_version}\n"
    assert result.stdout == expected_output, (
        f"Expected '{expected_output}', got '{result.stdout}'"
    )

    # Verify stderr is empty
    assert result.stderr == "", f"Expected empty stderr, got '{result.stderr}'"


def test_version_consistent_with_pyproject():
    """Test that the version matches what's defined in pyproject.toml."""
    # Get the version from package metadata
    package_version = importlib.metadata.version("gpt_copy")

    # Read the version from pyproject.toml (simple check)
    import tomllib
    from pathlib import Path

    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)

    pyproject_version = pyproject_data["project"]["version"]

    # Verify they match
    assert package_version == pyproject_version, (
        f"Package version '{package_version}' doesn't match pyproject.toml version '{pyproject_version}'"
    )
