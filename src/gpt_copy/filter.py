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
        # Track which patterns have matched at least once
        self._pattern_matched: dict[str, bool] = {}
        for rule in rules:
            if rule.pattern not in self._compiled_specs:
                # Expand brace expressions like {file1,file2} before compiling
                expanded_patterns = expand_braces(rule.pattern)
                self._compiled_specs[rule.pattern] = PathSpec.from_lines(
                    GitWildMatchPattern, expanded_patterns
                )
            # Initialize tracking for this pattern
            self._pattern_matched[rule.pattern] = False

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
        # Use PathSpec for glob matching with ** support
        spec = self._compiled_specs.get(pattern)
        if not spec:
            return False

        # If pattern ends with /, it should only match directories
        # For patterns like "dir/", match the directory and contents
        # For patterns like "dir/**/", match only directories at any depth under dir/
        if pattern.endswith("/"):
            if not is_dir:
                # Files should not match directory-only patterns
                # UNLESS the pattern also matches the file path (e.g., "dir/" matches "dir/file.txt")
                # Check if this is a simple directory pattern or has wildcards
                if "**" in pattern or "*" in pattern.rstrip("/"):
                    # Pattern has wildcards - only match if this is a directory
                    return False
                # Pattern is a simple directory like "node_modules/"
                # This should match contents too
                match_path = relpath
            else:
                # Match the directory with trailing /
                match_path = relpath + "/"
        else:
            # For non-directory patterns, match as-is
            match_path = relpath

        matched = spec.match_file(match_path)
        # Track if this pattern matched
        if matched:
            self._pattern_matched[pattern] = True
        return matched

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
        # If pattern starts with the directory path, it targets descendants
        if pattern.startswith(dir_relpath + "/"):
            return True

        # If dir is root level, any pattern could potentially match something under it
        if not dir_relpath or dir_relpath == ".":
            return True

        # If pattern contains ** at the start (like **/foo), it might match anywhere
        if pattern.startswith("**/"):
            return True

        # If pattern is just **, it matches everything
        if pattern == "**":
            return True

        # If the pattern has no directory component, it could match direct children
        if "/" not in pattern.rstrip("/"):
            return True

        # For patterns with directory components (like "build/reports/**"),
        # check if the pattern could possibly match under dir_relpath
        # Extract the first directory component of the pattern
        pattern_first_dir = pattern.split("/")[0]

        # Check if dir_relpath could contain this directory
        # For example:
        #   dir_relpath="node_modules", pattern="build/reports/**" -> False (different first dirs)
        #   dir_relpath="build", pattern="build/reports/**" -> True (pattern is under build)
        #   dir_relpath="", pattern="build/reports/**" -> True (pattern could be anywhere)

        # If the directory path starts with the pattern's first directory, it could match
        if (
            dir_relpath.startswith(pattern_first_dir + "/")
            or dir_relpath == pattern_first_dir
        ):
            return True

        # If the pattern's first directory starts with dir_relpath, it could match
        if pattern_first_dir.startswith(dir_relpath + "/"):
            return True

        # Otherwise, the paths are incompatible
        return False

    def get_unmatched_patterns(self) -> list[tuple[RuleKind, str]]:
        """
        Get a list of patterns that never matched any file or directory.

        Returns:
            List of (RuleKind, pattern) tuples for patterns that didn't match anything
        """
        unmatched = []
        for rule in self.rules:
            if not self._pattern_matched.get(rule.pattern, False):
                unmatched.append((rule.kind, rule.pattern))
        return unmatched


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
