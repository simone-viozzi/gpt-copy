#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from typing import TextIO

import click
import pygit2
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from tqdm import tqdm

from gpt_copy.filter import should_include_file


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


def find_git_repo(path: Path) -> pygit2.Repository | None:
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
        return pygit2.Repository(Path(repo_path).parent.as_posix())
    except pygit2.GitError:
        return None


def get_tracked_files(repo: pygit2.Repository) -> set[str]:
    """
    Get the set of tracked files in the given git repository.

    Args:
        repo (pygit2.Repository): The git repository.

    Returns:
        Set[str]: A set of tracked file paths.
    """
    return {entry.path for entry in repo.index}


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
            new_tracked = set()
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
    gitignore_specs = {}

    for dirpath, dirnames, filenames in tqdm(
        os.walk(root_path), desc="Scanning Directories"
    ):
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


def generate_tree(
    root_path: Path,
    gitignore_specs: dict[str, PathSpec],
    tracked_files: set[str] | None = None,
) -> str:
    """
    Generate a folder structure tree.

    Args:
        root_path (Path): The root path to start generating the tree.
        gitignore_specs (Dict[str, PathSpec]): The gitignore specifications.
        tracked_files (Optional[Set[str]]): The set of tracked files.

    Returns:
        str: The generated folder structure tree.
    """
    print("Generating folder structure tree...", file=sys.stderr)
    tree_lines = [root_path.name or str(root_path)]

    def _tree(dir_path: Path, prefix=""):
        try:
            entries = sorted(dir_path.iterdir())
        except OSError as e:
            print(f"Warning: cannot list {dir_path} due to error: {e}", file=sys.stderr)
            return

        for i, entry in enumerate(entries):
            if is_ignored(entry, gitignore_specs, root_path, tracked_files):
                continue

            connector = "└── " if i == len(entries) - 1 else "├── "
            tree_lines.append(prefix + connector + entry.name)

            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                _tree(entry, prefix + extension)

    _tree(root_path)
    return "\n".join(tree_lines)


def collect_files_content(
    root_path: Path,
    gitignore_specs: dict[str, PathSpec],
    output_file: str | None,
    tracked_files: set[str] | None,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
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

    Returns:
        Tuple[List[str], List[str]]: A tuple containing the file sections and unrecognized files.
    """
    print("Collecting file contents...", file=sys.stderr)
    file_sections: list[str] = []
    unrecognized_files: list[str] = []

    # Ensure include/exclude are lists.
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

            try:
                with full_file_path.open("r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception as e:
                print(
                    f"Skipping file {rel_path} due to read error: {e}",
                    file=sys.stderr,
                )
                continue

            language = infer_language(full_file_path)
            file_header = f"## File: `{rel_path}`\n*(Relative Path: `{rel_path}`)*"
            fenced_content = (
                f"```{language}\n{content}\n```" if language else f"```\n{content}\n```"
            )
            section = f"{file_header}\n\n{fenced_content}\n\n---\n"
            file_sections.append(section)

    return file_sections, unrecognized_files


def write_output(
    output: TextIO,
    tree_output: str,
    file_sections: list[str],
    unrecognized_files: list[str],
) -> None:
    """
    Write collected outputs to the specified output (file or stdout).

    Args:
        output (TextIO): The output stream.
        tree_output (str): The generated folder structure tree.
        file_sections (List[str]): The collected file sections.
        unrecognized_files (List[str]): The list of unrecognized files.
    """
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
def main(
    root_path: Path,
    output_file: str | None,
    force: bool,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> None:
    """
    Main function to start the script.

    Args:
        root_path (Path): The root path to start processing.
        output_file (Optional[str]): The output file path.
        force (bool): If True, ignore .gitignore and git-tracked files.
        include_patterns (Tuple[str, ...]): The tuple of include glob patterns.
        exclude_patterns (Tuple[str, ...]): The tuple of exclude glob patterns.
    """
    root_path = root_path.resolve()
    print(f"Starting script for directory: {root_path}", file=sys.stderr)
    gitignore_specs, tracked_files = get_ignore_settings(root_path, force)
    tree_output = generate_tree(root_path, gitignore_specs, tracked_files)
    file_sections, unrecognized_files = collect_files_content(
        root_path,
        gitignore_specs,
        output_file,
        tracked_files,
        include_patterns=list(include_patterns),
        exclude_patterns=list(exclude_patterns),
    )

    if output_file:
        print(f"Writing output to {output_file}...", file=sys.stderr)
        with open(output_file, "w", encoding="utf-8") as out:
            write_output(out, tree_output, file_sections, unrecognized_files)
    else:
        write_output(sys.stdout, tree_output, file_sections, unrecognized_files)

    print(f"All files merged into {output_file or 'stdout'}", file=sys.stderr)
    if unrecognized_files:
        print(
            "Some files were not recognized and were skipped. See 'Unrecognized Files' section.",
            file=sys.stderr,
        )
