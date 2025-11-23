# File: tests/test_file_filtering.py

from gpt_copy.filter import expand_braces, FilterEngine, Rule, RuleKind, Action


def test_expand_braces_no_braces():
    """Test that patterns without braces are returned as-is."""
    pattern = "src/*.py"
    assert expand_braces(pattern) == [pattern]


def test_expand_braces_simple():
    """Test simple brace expansion."""
    pattern = "src/{file1,file2}.py"
    expanded = expand_braces(pattern)
    assert "src/file1.py" in expanded
    assert "src/file2.py" in expanded
    assert len(expanded) == 2


def test_filter_engine_with_braces():
    """Test that FilterEngine supports brace expansion in patterns."""
    # Create a rule with brace expansion
    rules = [Rule(kind=RuleKind.INCLUDE, pattern="src/{file1,file2}.py")]
    engine = FilterEngine(rules)

    # Both expanded patterns should match
    assert engine.effective_action("src/file1.py", is_dir=False) == Action.INCLUDE
    assert engine.effective_action("src/file2.py", is_dir=False) == Action.INCLUDE
    # Non-matching patterns should use default (INCLUDE with no other rules)
    assert engine.effective_action("src/file3.py", is_dir=False) == Action.INCLUDE


def test_filter_engine_last_match_wins():
    """Test that FilterEngine implements last-match-wins semantics."""
    # Create rules: include *.py, then exclude __init__.py
    rules = [
        Rule(kind=RuleKind.INCLUDE, pattern="src/*.py"),
        Rule(kind=RuleKind.EXCLUDE, pattern="src/__init__.py"),
    ]
    engine = FilterEngine(rules)

    # src/main.py matches only first rule -> INCLUDE
    assert engine.effective_action("src/main.py", is_dir=False) == Action.INCLUDE
    # src/__init__.py matches both rules, last one wins -> EXCLUDE
    assert engine.effective_action("src/__init__.py", is_dir=False) == Action.EXCLUDE


def test_filter_engine_exclude_then_include():
    """Test that later includes can override earlier excludes."""
    # Create rules: exclude docs/*.md, then include docs/readme.md
    rules = [
        Rule(kind=RuleKind.EXCLUDE, pattern="docs/*.md"),
        Rule(kind=RuleKind.INCLUDE, pattern="docs/readme.md"),
    ]
    engine = FilterEngine(rules)

    # docs/readme.md matches both, last match wins -> INCLUDE
    assert engine.effective_action("docs/readme.md", is_dir=False) == Action.INCLUDE
    # docs/other.md matches only first rule -> EXCLUDE
    assert engine.effective_action("docs/other.md", is_dir=False) == Action.EXCLUDE


def test_filter_engine_tracks_unmatched_patterns():
    """Test that FilterEngine correctly tracks unmatched patterns."""
    rules = [
        Rule(kind=RuleKind.EXCLUDE, pattern="*.log"),
        Rule(kind=RuleKind.INCLUDE, pattern="*.txt"),
        Rule(kind=RuleKind.EXCLUDE, pattern="*.nonexistent"),
    ]
    engine = FilterEngine(rules)

    # Simulate matching some files
    engine.matches("*.log", "debug.log", is_dir=False)
    engine.matches("*.txt", "readme.txt", is_dir=False)

    # Get unmatched patterns
    unmatched = engine.get_unmatched_patterns()

    # Only *.nonexistent should be unmatched
    assert len(unmatched) == 1
    assert unmatched[0] == (RuleKind.EXCLUDE, "*.nonexistent")


def test_filter_engine_all_patterns_matched():
    """Test that no warning when all patterns match."""
    rules = [
        Rule(kind=RuleKind.EXCLUDE, pattern="*.log"),
        Rule(kind=RuleKind.INCLUDE, pattern="*.txt"),
    ]
    engine = FilterEngine(rules)

    # Simulate matching all patterns
    engine.matches("*.log", "debug.log", is_dir=False)
    engine.matches("*.txt", "readme.txt", is_dir=False)

    # Get unmatched patterns
    unmatched = engine.get_unmatched_patterns()

    # No patterns should be unmatched
    assert len(unmatched) == 0
