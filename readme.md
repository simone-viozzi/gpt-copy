# GPT Copy

## Overview
GPT Copy is a command-line tool that recursively scans a directory, collects readable files, and concatenates them into a single structured markdown stream. The output can be printed to stdout or written to a file, making it easy to feed codebases, documentation, or notes into language models like GPT.

## Features
- **Recursive Directory Scanning:** Respects `.gitignore` rules to selectively process files.
- **Structured Output:** Concatenates file contents into a structured markdown document with file-specific code fences.
- **File Filtering:** Supports glob-style include (`-i/--include`) and exclude (`-e/--exclude`) patterns for precise file selection.
- **Force Mode:** The `-f/--force` option bypasses ignore rules and Git-tracked file restrictions.
- **Line Numbering:** Zero-padded line numbers are added to each file's content by default (similar to `cat -n`). Use `--no-number` to disable.
- **Token Counting:** Includes a separate `tokens` CLI command to count the number of tokens in text using OpenAI’s `tiktoken` library with GPT-4o model encoding.
- **Integrated Token Analysis:** Use `--tokens` to display token counts for each file in the tree structure, with `--top-n` to filter and show only the files with the most tokens.

## Installation

### Using UV (Recommended)
Install globally using UV's tool system:

```sh
uv tool install git+https://github.com/simone-viozzi/gpt-copy.git
```

### Using Pip
Install directly from Git:

```sh
pip install git+https://github.com/simone-viozzi/gpt-copy.git
```

### Development Installation
For development, clone the repository and install in editable mode:

```sh
git clone https://github.com/simone-viozzi/gpt-copy.git
cd gpt-copy
uv sync --dev  # or pip install -e .[dev]
```

## Usage

### Basic Usage
Run the tool by specifying the target directory:

```sh
gpt-copy /path/to/directory
```

### Save Output to a File
Redirect the output to a file:

```sh
gpt-copy /path/to/directory -o output.md
```

### Advanced File Filtering
Fine-tune which files are processed using include and exclude options. Patterns follow gitignore-style glob syntax with support for `*`, `**`, and brace expansion.

#### Filter Options

- **`-i` or `--include`:** Include files/directories matching the pattern
- **`-e` or `--exclude`:** Exclude files/directories matching the pattern
- **`--exclude-dir`:** Exclude directories (automatically adds trailing `/`)

#### Pattern Matching Rules

1. **Last Match Wins:** If multiple patterns match a file, the last matching pattern determines whether it's included or excluded.
2. **Directory Patterns:** Patterns ending with `/` match directories and all their contents.
   - `node_modules/` excludes the directory and everything inside it
   - `build/` excludes the build directory and all files/subdirectories
3. **Wildcard Patterns:**
   - `*` matches any characters except `/`
   - `**` matches any characters including `/` (any depth)
   - `tests/*` matches direct children of tests directory
   - `**/*.log` matches all .log files at any depth
4. **Directory-Only Wildcards:** Patterns with wildcards ending in `/` match only directories
   - `tmp/**/` matches all directories under tmp/ at any depth, but not files

#### Examples

- **Exclude directories with all their contents:**
  ```sh
  gpt-copy . --exclude-dir tests --exclude-dir node_modules
  # or equivalently:
  gpt-copy . -e "tests/" -e "node_modules/"
  ```

- **Exclude specific directories but include subdirectories:**
  ```sh
  gpt-copy . -e "tests/*" -i "tests/**/"
  # Excludes direct children of tests/ but includes nested directories
  ```

- **Exclude all files then include specific ones:**
  ```sh
  gpt-copy . -e "**" -i "src/**/*.py"
  # Excludes everything, then includes Python files under src/
  ```

- **Complex filtering with multiple patterns:**
  ```sh
  gpt-copy . -e "build/**" -e "**/*.log" -i "build/reports/**"
  # Excludes build directory and all .log files, but includes build/reports/
  ```

- **Include only specific folder:**
  ```sh
  gpt-copy . -e "app/" -e "tests/" -e "notebooks/" -i "deployment/"
  # Excludes app, tests, notebooks, includes only deployment
  ```

### Force Mode (`-f` or `--force`)
Ignore `.gitignore` and Git-tracked file restrictions to process **all** files:

```sh
gpt-copy /path/to/directory -f
```

### Line Numbers (enabled by default)
Line numbering is **enabled by default** for the content of each file. Each line is prefixed with a zero-padded line number, similar to the Unix `cat -n` command.

**Basic usage (line numbers included):**
```sh
gpt-copy /path/to/directory
```

**Disable line numbers:**
```sh
gpt-copy /path/to/directory --no-number
```

### Count Tokens with `tokens`
Count the number of tokens in a given text using GPT-4o encoding. The command reads from a file or standard input.

**Examples:**
- Count tokens in a file:
  ```sh
  tokens file.txt
  ```
- Pipe output from `gpt-copy` into `tokens`:
  ```sh
  gpt-copy /path/to/directory | tokens
  ```

### Display Token Counts in Tree Structure
Display token counts for each file in the directory tree using the `--tokens` option:

```sh
gpt-copy /path/to/directory --tokens
```

**Filter by Top N Files by Token Count:**
Show only the files with the highest token counts:

```sh
gpt-copy /path/to/directory --tokens --top-n 5
```

**Combine with File Filtering:**
Use with include/exclude patterns to count tokens only for specific file types:

```sh
gpt-copy /path/to/directory --tokens --include "*.py" --top-n 3
```

## How It Works
1. **Collects `.gitignore` Rules:**
   Scans the directory for `.gitignore` files and applies the rules to skip ignored files unless the force mode is enabled.

2. **Generates a Structured File Tree:**
   Creates a visual representation of the directory structure.

3. **Reads and Formats Files:**
   - Detects file type based on extension.
   - Wraps file contents in appropriate markdown code fences.
   - Adds line numbers by default (can be disabled with `--no-number`).
   - Skips binary or unrecognized file types.

4. **Applies File Filtering:**
   Uses include and exclude glob patterns to determine which files to process, based on their paths relative to the root directory.

## Example Output
`````
# Folder Structure

```
project_root
├── main.py
├── README.md
└── subdir
    ├── config.yaml
    └── script.js
```

## File Contents

### File: `main.py`
*(Relative Path: `main.py`)*

```python
print("Hello, World!")
```

### File: `config.yaml`
*(Relative Path: `subdir/config.yaml`)*

```yaml
version: 1.0
enabled: true
```
`````

## Contributing
Contributions are welcome! If you'd like to contribute, please open a pull request with your proposed changes.

## License
This project is licensed under the [MIT License](LICENSE).
