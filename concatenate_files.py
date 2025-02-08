#!/usr/bin/env python3
import os
import sys
import click
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from tqdm import tqdm
from typing import Tuple, TextIO


def get_language_for_extension(file_ext: str) -> str | None:
    """
    Return the code fence language for a given file extension.
    If not recognized, return None (so we know to skip).
    """
    extension_map = {
        ".py": "python",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".md": "markdown",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
        ".bash": "bash",
        ".java": "java",
        ".cs": "csharp",
        ".rb": "ruby",
        ".go": "go",
        ".php": "php",
        ".html": "html",
        ".css": "css",
        ".txt": "plaintext",
        ".rs": "rust",
        ".toml": "toml",
        ".xml": "xml",
        ".kt": "kotlin",
        ".swift": "swift",
        ".tf": "hcl",
        ".lua": "lua",
        ".dockerfile": "dockerfile",
        ".pest": "pest",
        ".csv": "csv",
        ".ini": "ini",
        ".ijs": "jslang",
    }
    # Special-case Dockerfile (if the file name is literally "Dockerfile")
    if file_ext == "" and "Dockerfile" in extension_map:
        return extension_map[".dockerfile"]

    return extension_map.get(file_ext.lower(), None)


def collect_gitignore_specs(root_path: str) -> dict[str, PathSpec]:
    """
    Traverse directories and build a dictionary of PathSpec objects
    corresponding to each directory where a .gitignore file is found.
    Skip directories that are already ignored.
    """
    print("Collecting .gitignore rules per directory...", file=sys.stderr)
    gitignore_specs = {}

    for dirpath, dirnames, filenames in tqdm(os.walk(root_path), desc="Scanning Directories"):
        rel_path = os.path.relpath(dirpath, root_path)

        # Skip directory if it's ignored
        if is_ignored(dirpath, gitignore_specs, root_path):
            dirnames.clear()  # Prevents os.walk from descending into this directory
            continue

        all_patterns = [".git/"]  # Always ignore .git/

        if ".gitignore" in filenames:
            gitignore_path = os.path.join(dirpath, ".gitignore")
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    patterns = f.read().splitlines()
                all_patterns.extend(patterns)
            except Exception as e:
                print(
                    f"Warning: Could not read {gitignore_path} due to error: {e}",
                    file=sys.stderr,
                )

        # Create PathSpec for the directory
        gitignore_specs[rel_path] = PathSpec.from_lines(GitWildMatchPattern, all_patterns)

    return gitignore_specs



def is_ignored(path: str, gitignore_specs: dict[str, PathSpec], root_path: str) -> bool:
    """
    Check if a file or directory is ignored based on cascading .gitignore rules.
    """
    rel_path = os.path.relpath(path, root_path)
    
    # Traverse up the directory tree to apply relevant .gitignore rules
    parts = rel_path.split(os.sep)
    current_path = ""
    for part in parts:
        current_path = os.path.join(current_path, part)
        if current_path in gitignore_specs:
            if gitignore_specs[current_path].match_file(rel_path):
                return True
    
    return False


def generate_tree(root_path: str, gitignore_specs: dict[str, PathSpec]) -> str:
    """
    Generate a textual tree representation of the folder structure,
    excluding files/dirs matched by their respective .gitignore rules.
    """
    print("Generating folder structure tree...", file=sys.stderr)
    tree_lines = []

    def _tree(dir_path, prefix=""):
        try:
            entries = sorted(os.listdir(dir_path))
        except OSError as e:
            print(f"Warning: cannot list {dir_path} due to error: {e}", file=sys.stderr)
            return

        for i, entry in enumerate(entries):
            full_path = os.path.join(dir_path, entry)
            if is_ignored(full_path, gitignore_specs, root_path):
                continue

            connector = "└── " if i == len(entries) - 1 else "├── "
            tree_lines.append(prefix + connector + entry)

            if os.path.isdir(full_path):
                extension = "    " if i == len(entries) - 1 else "│   "
                _tree(full_path, prefix + extension)

    root_basename = os.path.basename(os.path.abspath(root_path)) or root_path
    tree_lines.append(root_basename)
    _tree(root_path)
    return "\n".join(tree_lines)


def collect_files_content(
    root_path: str,
    gitignore_specs: dict[str, PathSpec],
    output_file: str | None,
) -> Tuple[list[str], list[str]]:
    """
    Walk the directory structure, respecting gitignore, and collect
    file contents or note them as unrecognized.
    """
    print("Collecting file contents...", file=sys.stderr)
    file_sections = []
    unrecognized_files = []

    file_list = []
    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            file_list.append(os.path.join(dirpath, filename))

    for full_file_path in tqdm(file_list, desc="Processing Files"):
        if is_ignored(full_file_path, gitignore_specs, root_path):
            continue

        if output_file and (
            os.path.basename(full_file_path) == os.path.basename(output_file)
        ):
            continue

        rel_path = os.path.relpath(full_file_path, root_path)
        _, ext = os.path.splitext(full_file_path)
        language = get_language_for_extension(ext)

        if language:
            try:
                with open(full_file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                file_header = f"## File: `{rel_path}`\n*(Relative Path: `{rel_path}`)*"
                fenced_content = f"```{language}\n{content}\n```"
                section = f"{file_header}\n\n{fenced_content}\n\n---\n"
                file_sections.append(section)
            except Exception as e:
                print(
                    f"Skipping file {rel_path} due to read error: {e}", file=sys.stderr
                )
        else:
            unrecognized_files.append(rel_path)

    return file_sections, unrecognized_files


def write_output(
    output: TextIO,
    tree_output: str,
    file_sections: list[str],
    unrecognized_files: list[str],
) -> None:
    """
    Write the collected outputs to the specified output (file or stdout).
    """
    output.write("# Folder Structure\n\n")
    output.write("```\n")
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
    "root_path", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option(
    "-o",
    "--output",
    "output_file",
    default=None,
    help="Output file path (default: stdout)",
)
def main(root_path: str, output_file: str | None) -> None:
    print(f"Starting script for directory: {root_path}", file=sys.stderr)

    gitignore_specs = collect_gitignore_specs(root_path)
    tree_output = generate_tree(root_path, gitignore_specs)
    file_sections, unrecognized_files = collect_files_content(
        root_path, gitignore_specs, output_file
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
