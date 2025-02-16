# File: tests/test_file_filtering.py

from gpt_copy.filter import expand_braces, matches_any_pattern, should_include_file


def test_expand_braces_no_braces():
    pattern = "src/*.py"
    assert expand_braces(pattern) == [pattern]


def test_expand_braces_simple():
    pattern = "src/{file1,file2}.py"
    expanded = expand_braces(pattern)
    assert "src/file1.py" in expanded
    assert "src/file2.py" in expanded
    assert len(expanded) == 2


def test_matches_any_pattern():
    patterns = ["src/*.py", "docs/*.md"]
    assert matches_any_pattern("src/main.py", patterns) is True
    assert matches_any_pattern("docs/readme.md", patterns) is True
    assert matches_any_pattern("src/main.txt", patterns) is False


def test_should_include_file_with_includes_excludes():
    includes = ["src/*.py"]
    excludes = ["src/__init__.py"]
    # Should include: matches include and is not excluded.
    assert should_include_file("src/main.py", includes, excludes) is True
    # Should exclude: even though it matches include, it is explicitly excluded.
    assert should_include_file("src/__init__.py", includes, excludes) is False
    # With no includes, a file is included unless it is excluded.
    assert should_include_file("docs/readme.md", [], ["docs/*.md"]) is False
    assert should_include_file("docs/readme.md", [], []) is True
