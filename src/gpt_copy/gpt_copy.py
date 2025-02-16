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


def is_binary_file(file_path: Path, blocksize: int = 1024) -> bool:
    """
    Determine if a file is binary by reading a block of bytes.
    Checks for null bytes and the ratio of non-text characters.
    """
    try:
        with file_path.open("rb") as f:
            chunk = f.read(blocksize)
            if b"\0" in chunk:
                return True
            if not chunk:
                return False
            # Define acceptable text characters (printable ASCII + common whitespace)
            text_chars = bytes(range(32, 127)) + b"\n\r\t\b"
            non_text = sum(1 for byte in chunk if byte not in text_chars)
            # If more than 30% of the bytes are non-text, consider it binary.
            if (non_text / len(chunk)) > 0.30:
                return True
    except Exception:
        # If we cannot read the file, assume it's binary to be safe.
        return True
    return False


def infer_language(file_path: Path) -> str:
    """
    Infer a language hint from the file name or extension.
    Returns a language string if we can confidently hint one (e.g. for 'Dockerfile'),
    or an empty string otherwise.
    """
    # Special-case for Dockerfile (which has no extension)
    if file_path.name.lower() == "dockerfile":
        return "docker"
    # Optionally, you could add a few common extensions here.
    # For most files, returning an empty string lets the LLM decide.
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
    """Search for a Git repository in the given directory or its parents."""
    try:
        return pygit2.Repository(path.resolve().as_posix())
    except pygit2.GitError:
        return None


def get_tracked_files(repo: pygit2.Repository) -> set[str]:
    """Returns a set of all tracked files in the repository."""
    return {entry.path for entry in repo.index}


def collect_gitignore_specs(root_path: Path) -> dict[str, PathSpec]:
    """Traverse directories and build a dictionary of PathSpec objects for .gitignore rules."""
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
                patterns.append(".git/")  # Always ignore .git/
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
    Check if a file is ignored.

    - When Git-tracking info is available, that branch is used.
    - Otherwise, .gitignore rules are applied.

    (For directories, a trailing "/" is added so that patterns ending with "/"
    match as expected.)
    """
    rel_path = path.relative_to(root_path).as_posix()

    if tracked_files is not None:
        if path.is_dir():
            return not any(f.startswith(rel_path + "/") for f in tracked_files)
        return rel_path not in tracked_files

    # When using .gitignore rules, for directories add a trailing slash.
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
    """Generate a textual tree representation of the folder structure."""
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
    tracked_files: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Collect the contents of text files (skipping binary files) based on ignore rules.

    Every file that is not ignored and not binary is read and included in the output.
    If a language hint can be inferred (via infer_language), it is used; otherwise,
    the file is wrapped in a code fence with no language specifier.

    Returns:
      - A list of markdown-formatted sections for each file.
      - A list of file paths (as strings) for which the file was skipped because it was binary.
    """
    print("Collecting file contents...", file=sys.stderr)
    file_sections: list[str] = []
    unrecognized_files: list[str] = []

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            full_file_path = Path(dirpath) / filename

            if is_ignored(full_file_path, gitignore_specs, root_path, tracked_files):
                continue

            # Avoid reprocessing the output file if it's in the same directory.
            if output_file and (full_file_path.name == Path(output_file).name):
                continue

            rel_path = full_file_path.relative_to(root_path)

            # Skip binary files.
            if is_binary_file(full_file_path):
                unrecognized_files.append(rel_path.as_posix())
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
            if language:
                fenced_content = f"```{language}\n{content}\n```"
            else:
                fenced_content = f"```\n{content}\n```"
            section = f"{file_header}\n\n{fenced_content}\n\n---\n"
            file_sections.append(section)

    return file_sections, unrecognized_files


def write_output(
    output: TextIO,
    tree_output: str,
    file_sections: list[str],
    unrecognized_files: list[str],
) -> None:
    """Write collected outputs to the specified output (file or stdout)."""
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
def main(root_path: Path, output_file: str | None) -> None:
    print(f"Starting script for directory: {root_path}", file=sys.stderr)

    repo = find_git_repo(root_path)
    tracked_files = get_tracked_files(repo) if repo else None
    gitignore_specs = {} if repo else collect_gitignore_specs(root_path)

    tree_output = generate_tree(root_path, gitignore_specs, tracked_files)
    file_sections, unrecognized_files = collect_files_content(
        root_path, gitignore_specs, output_file, tracked_files
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


if __name__ == "__main__":
    main()
