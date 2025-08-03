#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import TextIO
import importlib.metadata

import click
import pygit2
from pygit2 import Repository  # type: ignore
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from tqdm import tqdm

from gpt_copy.filter import should_include_file, matches_any_pattern
from dataclasses import dataclass
from typing import List


@dataclass
class FileInfo:
    """Information about a file including path and token count."""
    path: Path
    relative_path: str
    token_count: int
    is_directory: bool = False


def count_tokens_safe(text: str) -> int:
    """
    Count tokens using tiktoken if available, otherwise use a simple estimation.
    
    Args:
        text (str): The text to count tokens for.
        
    Returns:
        int: The estimated number of tokens.
    """
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
        tokens = enc.encode(text)
        return len(tokens)
    except Exception:
        # Fallback to simple estimation if tiktoken fails
        # Rough approximation: ~4 characters per token for English text
        char_count = len(text)
        estimated_tokens = max(1, char_count // 4)
        return estimated_tokens


def add_line_numbers(text: str) -> str:
    """
    Add line numbers to each line of the given text.
    Line numbers are padded with zeros based on the total number of lines.

    For example, if the file has 120 lines, the first line will be "001: <line content>".

    Args:
        text (str): The original text.

    Returns:
        str: The text with line numbers added.
    """
    lines = text.splitlines()
    if not lines:
        return text
    width = len(str(len(lines)))
    numbered_lines = [
        f"{str(i + 1).zfill(width)}: {line}" for i, line in enumerate(lines)
    ]
    return "\n".join(numbered_lines)


def is_binary_file(file_path: Path, blocksize: int = 1024) -> bool:
    """
    Determine if a file is binary by reading a block of bytes.
    Checks for null bytes and the ratio of non-text characters.

    Args:
        file_path (Path): The path to the file.
        blocksize (int): The number of bytes to read for checking. Default is 1024.

    Returns:
        bool: True if the file is binary, False otherwise.
    """
    try:
        with file_path.open("rb") as f:
            chunk = f.read(blocksize)
            if b"\0" in chunk:
                return True
            if not chunk:
                return False
            text_chars = bytes(range(32, 127)) + b"\n\r\t\b"
            non_text = sum(1 for byte in chunk if byte not in text_chars)
            if (non_text / len(chunk)) > 0.30:
                return True
    except Exception:
        return True
    return False


def _get_visible_entries(
    dir_path: Path,
    gitignore_specs: dict[str, PathSpec],
    root_path: Path,
    tracked_files: set[str] | None,
) -> list[Path]:
    """
    Return a sorted list of entries in dir_path that are not gitignored.
    """
    try:
        entries = sorted(dir_path.iterdir())
    except OSError as e:
        print(f"Warning: cannot list {dir_path} due to error: {e}", file=sys.stderr)
        return []
    return [
        entry
        for entry in entries
        if not is_ignored(entry, gitignore_specs, root_path, tracked_files)
    ]


def _compress_directory(
    dir_path: Path,
    gitignore_specs: dict[str, PathSpec],
    root_path: Path,
    tracked_files: set[str] | None,
    prefix: str,
    max_items: int = 3,
) -> list[str]:
    """
    Return a list of tree lines for a compressed view of an excluded directory.
    It shows up to max_items immediate children followed by an ellipsis if there are more.
    """
    lines: list[str] = []
    try:
        children = sorted(dir_path.iterdir())
    except OSError as e:
        print(f"Warning: cannot list {dir_path} due to error: {e}", file=sys.stderr)
        return lines

    # Filter out gitignored children.
    children = [
        child
        for child in children
        if not is_ignored(child, gitignore_specs, root_path, tracked_files)
    ]
    count = 0
    for child in children:
        if count >= max_items:
            lines.append(prefix + "[...]")
            break
        # Using a simple connector since no recursive expansion is needed.
        lines.append(prefix + "└── " + child.name)
        count += 1
    return lines


def _process_file(
    full_file_path: Path, root_path: Path, line_numbers: bool
) -> tuple[str, str]:
    """
    Process a single file to read its content, optionally add line numbers,
    and return its relative path and a markdown section.
    """
    rel_path = full_file_path.relative_to(root_path).as_posix()
    try:
        with full_file_path.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        print(f"Skipping file {rel_path} due to read error: {e}", file=sys.stderr)
        return "", ""

    if line_numbers:
        content = add_line_numbers(content)

    language = infer_language(full_file_path)
    file_header = f"## File: `{rel_path}`\n*(Relative Path: `{rel_path}`)*"
    fenced_content = (
        f"```{language}\n{content}\n```" if language else f"```\n{content}\n```"
    )
    section = f"{file_header}\n\n{fenced_content}\n\n---\n"
    return rel_path, section


def infer_language(file_path: Path) -> str:
    """
    Infer a language hint from the file name or extension.

    Args:
        file_path (Path): The path to the file.

    Returns:
        str: The inferred language hint.
    """
    if file_path.name.lower() == "dockerfile":
        return "docker"
    minimal_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".cpp": "cpp",
        ".c": "c",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
    }
    return minimal_map.get(file_path.suffix.lower(), "")


def find_git_repo(path: Path) -> Repository | None:
    """
    Find the git repository for the given path.

    Args:
        path (Path): The path to search for a git repository.

    Returns:
        Optional[pygit2.Repository]: The found git repository or None if not found.
    """
    repo_path = pygit2.discover_repository(path.as_posix())
    if repo_path is None:
        return None
    try:
        return Repository(Path(repo_path).parent.as_posix())
    except pygit2.GitError:
        return None


def get_tracked_files(repo: Repository) -> set[str]:
    """
    Get the set of tracked files in the given git repository.

    Args:
        repo (Repository): The git repository.

    Returns:
        Set[str]: A set of tracked file paths.
    """
    return {entry.path for entry in repo.index}  # type: ignore


def get_ignore_settings(
    root_path: Path, force: bool
) -> tuple[dict[str, PathSpec], set[str] | None]:
    """
    Get the ignore settings based on .gitignore files and git-tracked files.

    Args:
        root_path (Path): The root path to start searching.
        force (bool): If True, ignore .gitignore and git-tracked files.

    Returns:
        Tuple[Dict[str, PathSpec], Optional[Set[str]]]: A tuple containing the gitignore specs and tracked files.
    """
    if force:
        return {}, None

    repo = find_git_repo(root_path)
    if repo:
        repo_root = Path(repo.workdir)
        all_tracked = get_tracked_files(repo)
        try:
            subfolder_relative = root_path.relative_to(repo_root)
        except ValueError:
            subfolder_relative = None

        if subfolder_relative is not None:
            new_tracked: set[str] = set()
            for f in all_tracked:
                file_path = Path(f)
                try:
                    rel_to_subfolder = file_path.relative_to(subfolder_relative)
                    new_tracked.add(rel_to_subfolder.as_posix())
                except ValueError:
                    continue
            tracked_files = new_tracked
        else:
            tracked_files = all_tracked
        return {}, tracked_files
    else:
        return collect_gitignore_specs(root_path), None


def collect_gitignore_specs(root_path: Path) -> dict[str, PathSpec]:
    """
    Collect .gitignore specifications for each directory.

    Args:
        root_path (Path): The root path to start searching.

    Returns:
        Dict[str, PathSpec]: A dictionary mapping directory paths to PathSpec objects.
    """
    print("Collecting .gitignore rules per directory...", file=sys.stderr)
    gitignore_specs: dict[str, PathSpec] = {}

    for dirpath, _, _ in tqdm(os.walk(root_path), desc="Scanning Directories"):
        dirpath = Path(dirpath)
        rel_path = dirpath.relative_to(root_path)
        gitignore_file = dirpath / ".gitignore"
        if gitignore_file.exists():
            try:
                with gitignore_file.open("r", encoding="utf-8") as f:
                    patterns = f.read().splitlines()
                patterns.append(".git/")
                gitignore_specs[rel_path.as_posix()] = PathSpec.from_lines(
                    GitWildMatchPattern, patterns
                )
            except Exception as e:
                print(
                    f"Warning: Could not read {gitignore_file} due to error: {e}",
                    file=sys.stderr,
                )

    return gitignore_specs


def is_ignored(
    path: Path,
    gitignore_specs: dict[str, PathSpec],
    root_path: Path,
    tracked_files: set[str] | None = None,
) -> bool:
    """
    Check if a path is ignored based on gitignore specs and tracked files.

    Args:
        path (Path): The path to check.
        gitignore_specs (Dict[str, PathSpec]): The gitignore specifications.
        root_path (Path): The root path.
        tracked_files (Optional[Set[str]]): The set of tracked files.

    Returns:
        bool: True if the path is ignored, False otherwise.
    """
    rel_path = path.relative_to(root_path).as_posix()

    if tracked_files is not None:
        if path.is_dir():
            return not any(f.startswith(rel_path + "/") for f in tracked_files)
        return rel_path not in tracked_files

    rel_path_for_match = rel_path + "/" if path.is_dir() else rel_path
    for spec in gitignore_specs.values():
        if spec.match_file(rel_path_for_match):
            return True

    return False


def collect_file_info_with_tokens(
    root_path: Path,
    gitignore_specs: dict[str, PathSpec],
    tracked_files: set[str] | None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> List[FileInfo]:
    """
    Collect file information including token counts for all files.
    
    Args:
        root_path (Path): The root path to start collecting files.
        gitignore_specs (Dict[str, PathSpec]): The gitignore specifications.
        tracked_files (Optional[Set[str]]): The set of tracked files.
        include_patterns (Optional[List[str]]): The list of include glob patterns.
        exclude_patterns (Optional[List[str]]): The list of exclude glob patterns.
    
    Returns:
        List[FileInfo]: List of FileInfo objects with token counts.
    """
    print("Collecting file information with token counts...", file=sys.stderr)
    file_infos: List[FileInfo] = []
    
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        current_dir = Path(dirpath)
        
        # Process files in current directory
        for filename in filenames:
            full_file_path = current_dir / filename
            
            if is_ignored(full_file_path, gitignore_specs, root_path, tracked_files):
                continue
                
            rel_path = full_file_path.relative_to(root_path).as_posix()
            
            # Apply include/exclude filters
            if not should_include_file(rel_path, include_patterns, exclude_patterns):
                continue
                
            if is_binary_file(full_file_path):
                # Still include binary files but with 0 tokens
                file_infos.append(FileInfo(
                    path=full_file_path,
                    relative_path=rel_path,
                    token_count=0,
                    is_directory=False
                ))
                continue
            
            # Count tokens for text files
            try:
                with full_file_path.open("r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                token_count = count_tokens_safe(content)
            except Exception as e:
                print(f"Warning: Could not read {rel_path} for token counting: {e}", file=sys.stderr)
                token_count = 0
            
            file_infos.append(FileInfo(
                path=full_file_path,
                relative_path=rel_path,
                token_count=token_count,
                is_directory=False
            ))
    
    return file_infos


def calculate_directory_tokens(dir_structure, path_parts=()):
    """
    Calculate total tokens for directories recursively.
    
    Args:
        dir_structure: Dictionary representing directory structure
        path_parts: Tuple of path parts for current directory
    
    Returns:
        int: Total token count for the directory
    """
    total_tokens = 0
    for name, item in dir_structure.items():
        if isinstance(item, dict):
            # Recursively calculate tokens for subdirectory
            total_tokens += calculate_directory_tokens(item, path_parts + (name,))
        else:
            # File - add its token count
            total_tokens += item.token_count
    return total_tokens


def generate_tree_with_tokens(
    root_path: Path,
    file_infos: List[FileInfo],
    gitignore_specs: dict[str, PathSpec],
    tracked_files: set[str] | None = None,
    exclude_patterns: list[str] | None = None,
    top_n: int | None = None,
) -> str:
    """
    Generate a folder structure tree with token counts.
    
    Args:
        root_path (Path): The root path to start generating the tree.
        file_infos (List[FileInfo]): List of file information with token counts.
        gitignore_specs (Dict[str, PathSpec]): The gitignore specifications.
        tracked_files (Optional[Set[str]]): The set of tracked files.
        exclude_patterns (Optional[List[str]]): Glob patterns to exclude files/directories.
        top_n (Optional[int]): Show only top N files by token count.
    
    Returns:
        str: The generated folder structure tree with token counts.
    """
    print("Generating folder structure tree with token counts...", file=sys.stderr)
    
    # If top_n is specified, get the top N files but keep tree structure
    top_files_set = None
    if top_n is not None:
        top_files = sorted(file_infos, key=lambda x: x.token_count, reverse=True)[:top_n]
        top_files_set = {f.relative_path for f in top_files}
    
    # Create a mapping of directories to their files
    dir_structure = {}
    for file_info in file_infos:
        # If top_n is specified, only include files in the top N
        if top_files_set is not None and file_info.relative_path not in top_files_set:
            continue
            
        parts = Path(file_info.relative_path).parts
        current = dir_structure
        
        # Build directory structure
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Add file to its directory
        if len(parts) > 0:
            filename = parts[-1]
            current[filename] = file_info
    
    # Calculate directory token counts
    root_tokens = calculate_directory_tokens(dir_structure)
    
    # Build a tree structure showing token counts
    tree_lines = [f"{root_path.name or str(root_path)} (directory)"]
    if root_tokens > 0:
        tree_lines[0] = f"{root_path.name or str(root_path)} ({root_tokens} tokens)"
    
    def _add_tree_items(items, prefix="", is_last_at_level=True):
        """Recursively add tree items with token counts."""
        # Separate directories and files, then sort each group
        directories = []
        files = []
        
        for name, item in items.items():
            if isinstance(item, dict):
                dir_tokens = calculate_directory_tokens(item)
                directories.append((name, item, dir_tokens))
            else:
                files.append((name, item, item.token_count))
        
        # Sort directories by token count (descending), then files by token count (descending)
        directories.sort(key=lambda x: x[2], reverse=True)
        files.sort(key=lambda x: x[2], reverse=True)
        
        # Combine directories and files - directories first, then files (both sorted by tokens)
        all_items = [(name, item, tokens, True) for name, item, tokens in directories] + \
                   [(name, item, tokens, False) for name, item, tokens in files]
        
        for idx, (name, item, tokens, is_dir) in enumerate(all_items):
            is_last = idx == len(all_items) - 1
            connector = "└── " if is_last else "├── "
            
            if is_dir:
                # Directory with token count
                tree_lines.append(f"{prefix}{connector}{name}/ ({tokens} tokens)")
                extension = "    " if is_last else "│   "
                _add_tree_items(item, prefix + extension, is_last)
            else:
                # File with token count
                tree_lines.append(f"{prefix}{connector}{name} ({tokens} tokens)")
    
    _add_tree_items(dir_structure)
    
    if top_n is not None:
        total_files = len([f for f in file_infos if not f.is_directory])
        tree_lines.append(f"\nShowing top {min(top_n, total_files)} files by token count")
    
    return "\n".join(tree_lines)


def generate_tree(
    root_path: Path,
    gitignore_specs: dict[str, PathSpec],
    tracked_files: set[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> str:
    """
    Generate a folder structure tree.

    Directories that match any of the provided exclude_patterns (specified via the -e/--exclude option)
    will be displayed in a compressed form: only one level of their children is shown (up to a maximum number),
    followed by an ellipsis "[...]" if there are additional items. Gitignored files (or directories) are never shown.

    Args:
        root_path (Path): The root path to start generating the tree.
        gitignore_specs (Dict[str, PathSpec]): The gitignore specifications.
        tracked_files (Optional[Set[str]]): The set of tracked files (if applicable).
        exclude_patterns (Optional[List[str]]): Glob patterns to exclude files/directories.

    Returns:
        str: The generated folder structure tree.
    """
    print("Generating folder structure tree...", file=sys.stderr)
    tree_lines = [root_path.name or str(root_path)]
    exclude_patterns = exclude_patterns or []

    def _tree(dir_path: Path, prefix: str = ""):
        visible_entries = _get_visible_entries(
            dir_path, gitignore_specs, root_path, tracked_files
        )
        for idx, entry in enumerate(visible_entries):
            connector = "└── " if idx == len(visible_entries) - 1 else "├── "
            if entry.is_dir():
                rel_path = entry.relative_to(root_path).as_posix()
                # Check if the directory is excluded by the -e option.
                if exclude_patterns and matches_any_pattern(rel_path, exclude_patterns):
                    tree_lines.append(prefix + connector + entry.name)
                    comp_lines = _compress_directory(
                        entry,
                        gitignore_specs,
                        root_path,
                        tracked_files,
                        prefix + "    ",
                    )
                    tree_lines.extend(comp_lines)
                else:
                    tree_lines.append(prefix + connector + entry.name)
                    extension = "    " if idx == len(visible_entries) - 1 else "│   "
                    _tree(entry, prefix + extension)
            else:
                tree_lines.append(prefix + connector + entry.name)

    _tree(root_path)
    return "\n".join(tree_lines)


def collect_files_content(
    root_path: Path,
    gitignore_specs: dict[str, PathSpec],
    output_file: str | None,
    tracked_files: set[str] | None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    line_numbers: bool = False,
) -> tuple[list[str], list[str]]:
    """
    Collect the contents of text files (skipping binary files) based on ignore rules
    and the include/exclude glob patterns.

    Args:
        root_path (Path): The root path to start collecting files.
        gitignore_specs (Dict[str, PathSpec]): The gitignore specifications.
        output_file (Optional[str]): The output file path.
        tracked_files (Optional[Set[str]]): The set of tracked files.
        include_patterns (Optional[List[str]]): The list of include glob patterns.
        exclude_patterns (Optional[List[str]]): The list of exclude glob patterns.
        line_numbers (bool): If True, adds line numbers to file contents.

    Returns:
        Tuple[List[str], List[str]]: A tuple containing the file sections and unrecognized files.
    """
    print("Collecting file contents...", file=sys.stderr)
    file_sections: list[str] = []
    unrecognized_files: list[str] = []

    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or []

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            full_file_path = Path(dirpath) / filename

            if is_ignored(full_file_path, gitignore_specs, root_path, tracked_files):
                continue

            # Avoid reprocessing the output file.
            if output_file and (full_file_path.name == Path(output_file).name):
                continue

            rel_path = full_file_path.relative_to(root_path).as_posix()

            # Apply include/exclude filters.
            if not should_include_file(rel_path, include_patterns, exclude_patterns):
                continue

            if is_binary_file(full_file_path):
                unrecognized_files.append(rel_path)
                continue

            # Use helper to process the file.
            _, section = _process_file(full_file_path, root_path, line_numbers)
            if section:
                file_sections.append(section)

    return file_sections, unrecognized_files


def write_output(
    output: TextIO,
    tree_output: str,
    file_sections: list[str],
    unrecognized_files: list[str],
    tree_only: bool = False,
) -> None:
    """
    Write collected outputs to the specified output (file or stdout).

    Args:
        output (TextIO): The output stream.
        tree_output (str): The generated folder structure tree.
        file_sections (List[str]): The collected file sections.
        unrecognized_files (List[str]): The list of unrecognized files.
        tree_only (bool): If True, only output the tree structure.
    """
    if tree_only:
        # Only output the tree structure without markdown headers
        output.write(tree_output)
        output.write("\n")
    else:
        # Original behavior: output everything with markdown formatting
        output.write("# Folder Structure\n\n```\n")
        output.write(tree_output)
        output.write("\n```\n\n")

        for section in file_sections:
            output.write(section)

        if unrecognized_files:
            output.write("# Unrecognized Files\n\n")
            output.write(
                "The following files were not recognized by extension and were skipped:\n\n"
            )
            for rel_path in unrecognized_files:
                output.write(f"- `{rel_path}`\n")


@click.command()
@click.version_option(version=importlib.metadata.version("gpt_copy"))
@click.argument(
    "root_path",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        path_type=Path,
    ),
)
@click.option(
    "-o",
    "--output",
    "output_file",
    default=None,
    help="Output file path (default: stdout)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force generation: ignore .gitignore and Git-tracked files",
)
@click.option(
    "-i",
    "--include",
    "include_patterns",
    multiple=True,
    help="Glob pattern(s) to include files (e.g., 'src/*.py', 'src/{module1,module2}.py')",
)
@click.option(
    "-e",
    "--exclude",
    "exclude_patterns",
    multiple=True,
    help="Glob pattern(s) to exclude files (e.g., 'src/tests/*')",
)
@click.option(
    "--no-number",
    "no_line_numbers",
    is_flag=True,
    default=False,
    help="Disable line numbers for file content.",
)
@click.option(
    "--tree-only",
    is_flag=True,
    default=False,
    help="Output only the folder structure tree without file contents.",
)
@click.option(
    "--tokens",
    is_flag=True,
    default=False,
    help="Display token counts for each file in the tree structure.",
)
@click.option(
    "--top-n",
    type=int,
    default=None,
    help="When used with --tokens, show only the top N files by token count.",
)
def main(
    root_path: Path,
    output_file: str | None,
    force: bool,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    no_line_numbers: bool,
    tree_only: bool,
    tokens: bool,
    top_n: int | None,
) -> None:
    """
    Main function to start the script.

    Args:
        root_path (Path): The root path to start processing.
        output_file (Optional[str]): The output file path.
        force (bool): If True, ignore .gitignore and Git-tracked files.
        include_patterns (Tuple[str, ...]): The tuple of include glob patterns.
        exclude_patterns (Tuple[str, ...]): The tuple of exclude glob patterns.
        no_line_numbers (bool): If True, disable line numbers.
        tree_only (bool): If True, output only the folder structure tree.
        tokens (bool): If True, display token counts for each file in the tree.
        top_n (Optional[int]): When used with tokens, show only top N files by token count.
    """

    root_path = root_path.resolve()
    print(f"Starting script for directory: {root_path}", file=sys.stderr)
    gitignore_specs, tracked_files = get_ignore_settings(root_path, force)
    
    if tokens:
        # Use token-aware tree generation
        file_infos = collect_file_info_with_tokens(
            root_path,
            gitignore_specs,
            tracked_files,
            include_patterns=list(include_patterns),
            exclude_patterns=list(exclude_patterns),
        )
        tree_output = generate_tree_with_tokens(
            root_path,
            file_infos,
            gitignore_specs,
            tracked_files,
            list(exclude_patterns),
            top_n,
        )
        # When showing tokens, we don't need the file contents
        file_sections = []
        unrecognized_files = []
    else:
        # Use regular tree generation
        tree_output = generate_tree(
            root_path, gitignore_specs, tracked_files, list(exclude_patterns)
        )
        
        if tree_only:
            # Only output the tree structure
            file_sections = []
            unrecognized_files = []
        else:
            # Collect file contents as usual
            file_sections, unrecognized_files = collect_files_content(
                root_path,
                gitignore_specs,
                output_file,
                tracked_files,
                include_patterns=list(include_patterns),
                exclude_patterns=list(exclude_patterns),
                line_numbers=not no_line_numbers,
            )

    if output_file:
        print(f"Writing output to {output_file}...", file=sys.stderr)
        with open(output_file, "w", encoding="utf-8") as out:
            write_output(out, tree_output, file_sections, unrecognized_files, tree_only)
    else:
        write_output(sys.stdout, tree_output, file_sections, unrecognized_files, tree_only)

    print(f"All files merged into {output_file or 'stdout'}", file=sys.stderr)
    if unrecognized_files:
        print(
            "Some files were not recognized and were skipped. See 'Unrecognized Files' section.",
            file=sys.stderr,
        )
