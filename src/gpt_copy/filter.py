import re
import fnmatch


def expand_braces(pattern: str) -> list[str]:
    """
    Expand a pattern containing simple brace expressions.

    For example, "src/{file1,file2}.py" becomes ["src/file1.py", "src/file2.py"].
    This minimal implementation does not support nested braces.

    Args:
        pattern (str): The pattern containing brace expressions.

    Returns:
        List[str]: A list of expanded patterns.
    """
    match = re.search(r"\{([^}]+)\}", pattern)
    if not match:
        return [pattern]
    pre = pattern[: match.start()]
    post = pattern[match.end() :]
    options = match.group(1).split(",")
    patterns: list[str] = []
    for option in options:
        # Recursively expand in case of multiple braces.
        patterns.extend(expand_braces(pre + option + post))
    return patterns


def matches_any_pattern(rel_path: str, patterns: list[str]) -> bool:
    """
    Return True if the given relative path matches any of the provided glob patterns.
    Each pattern is expanded using expand_braces to support brace expansion.

    Args:
        rel_path (str): The relative path to check.
        patterns (List[str]): A list of glob patterns.

    Returns:
        bool: True if the path matches any pattern, False otherwise.
    """
    for pattern in patterns:
        expanded_patterns = expand_braces(pattern)
        for pat in expanded_patterns:
            if fnmatch.fnmatch(rel_path, pat):
                return True
    return False


def should_include_file(
    rel_path: str, includes: list[str], excludes: list[str]
) -> bool:
    """
    Determine if a file should be included based on include and exclude glob patterns.

    - If includes is not empty, the file must match at least one include pattern.
    - If the file matches any exclude pattern, it is excluded.

    Args:
        rel_path (str): The relative path of the file.
        includes (List[str]): A list of include glob patterns.
        excludes (List[str]): A list of exclude glob patterns.

    Returns:
        bool: True if the file should be included, False otherwise.
    """
    # Exclude takes precedence.
    if excludes and matches_any_pattern(rel_path, excludes):
        return False
    if includes:
        return matches_any_pattern(rel_path, includes)
    return True
