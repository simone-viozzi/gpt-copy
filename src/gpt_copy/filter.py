import re
from dataclasses import dataclass
from enum import Enum
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern


class RuleKind(Enum):
    """Type of filter rule."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    EXCLUDE_DIR = "exclude_dir"


class Action(Enum):
    """Action to take on a path."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


@dataclass
class Rule:
    """A filtering rule with a kind and pattern."""

    kind: RuleKind
    pattern: str

    def __post_init__(self):
        """Normalize patterns ending with / for directory-only matching."""
        # For EXCLUDE_DIR, ensure trailing slash for consistency
        if self.kind == RuleKind.EXCLUDE_DIR and not self.pattern.endswith("/"):
            self.pattern = self.pattern + "/"


class FilterEngine:
    """
    Engine for evaluating include/exclude rules with last-match-wins semantics.

    Implements the filtering logic from the issue specification:
    - Patterns are glob-style, relative to scan root
    - Last matching rule wins
    - Conservative directory traversal (don't prune if later includes might match)
    """

    def __init__(self, rules: list[Rule]):
        """
        Initialize the filter engine with an ordered list of rules.

        Args:
            rules: List of Rule objects in CLI order (first to last)
        """
        self.rules = rules
        # Pre-compile patterns for performance, expanding brace expressions
        self._compiled_specs: dict[str, PathSpec] = {}
        for rule in rules:
            if rule.pattern not in self._compiled_specs:
                # Expand brace expressions like {file1,file2} before compiling
                expanded_patterns = expand_braces(rule.pattern)
                self._compiled_specs[rule.pattern] = PathSpec.from_lines(
                    GitWildMatchPattern, expanded_patterns
                )

    def matches(self, pattern: str, relpath: str, is_dir: bool) -> bool:
        """
        Check if a pattern matches a relative path.

        Args:
            pattern: Glob pattern (may end with / for dir-only)
            relpath: Relative path from scan root
            is_dir: Whether the path is a directory

        Returns:
            True if the pattern matches the path
        """
        # If pattern ends with /, only match directories
        if pattern.endswith("/"):
            if not is_dir:
                return False
            # Match the pattern against the path with trailing /
            match_path = relpath + "/"
        else:
            # For files, match as-is. For dirs, try both with and without /
            match_path = relpath

        # Use PathSpec for glob matching with ** support
        spec = self._compiled_specs.get(pattern)
        if spec:
            return spec.match_file(match_path)
        return False

    def effective_action(self, relpath: str, is_dir: bool) -> Action:
        """
        Determine the effective action for a path using last-match-wins.

        Args:
            relpath: Relative path from scan root
            is_dir: Whether the path is a directory

        Returns:
            Action.INCLUDE or Action.EXCLUDE
        """
        action = Action.INCLUDE  # Default action

        for rule in self.rules:
            if self.matches(rule.pattern, relpath, is_dir):
                if rule.kind == RuleKind.INCLUDE:
                    action = Action.INCLUDE
                else:  # EXCLUDE or EXCLUDE_DIR
                    action = Action.EXCLUDE

        return action

    def may_have_late_include_descendant(self, relpath: str) -> bool:
        """
        Check if any later INCLUDE rule could match a descendant of this directory.

        This is used for conservative traversal: even if a directory is excluded,
        we keep traversing if a later include might match something inside.

        Args:
            relpath: Relative path of the directory

        Returns:
            True if we should keep traversing this directory
        """
        # Find the last rule that matched this directory
        last_idx_for_dir = -1
        for i, rule in enumerate(self.rules):
            if self.matches(rule.pattern, relpath, is_dir=True):
                last_idx_for_dir = i

        # Check if any INCLUDE rule after the last match could match a descendant
        start_i = last_idx_for_dir + 1 if last_idx_for_dir >= 0 else 0

        for i in range(start_i, len(self.rules)):
            rule = self.rules[i]
            if rule.kind != RuleKind.INCLUDE:
                continue
            if self._include_can_match_descendant(rule.pattern, relpath):
                return True

        return False

    def _include_can_match_descendant(self, pattern: str, dir_relpath: str) -> bool:
        """
        Conservative check: could this pattern match any descendant of dir_relpath?

        Args:
            pattern: The include pattern
            dir_relpath: The directory path

        Returns:
            True if the pattern could potentially match a descendant
        """
        # If pattern contains **, it might match deep descendants
        if "**" in pattern:
            return True

        # If pattern starts with the directory path, it targets descendants
        if pattern.startswith(dir_relpath + "/"):
            return True

        # If the pattern has no directory component and dir is not nested,
        # it could match direct children
        if "/" not in pattern.rstrip("/"):
            return True

        # For other cases, be conservative - allow traversal
        # This includes patterns like "data/*.csv" which might match if dir_relpath is "" or "data"
        return True


# Legacy functions for backward compatibility with brace expansion
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
