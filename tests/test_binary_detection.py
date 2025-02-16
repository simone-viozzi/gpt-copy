from pathlib import Path

from gpt_copy.gpt_copy import is_binary_file


def test_is_binary_file_with_text(tmp_path: Path):
    # Create a simple text file.
    text_file = tmp_path / "text.txt"
    text_file.write_text("This is a simple text file.", encoding="utf-8")
    assert not is_binary_file(text_file)


def test_is_binary_file_with_binary(tmp_path: Path):
    # Create a binary file with some null bytes.
    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
    assert is_binary_file(binary_file)
