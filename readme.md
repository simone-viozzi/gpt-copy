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

## Installation
Ensure you have Python 3 installed. You can install the dependencies using:

```sh
pip install -r requirements.txt
```

Alternatively, install directly from Git:

```sh
pip install git+https://github.com/simone-viozzi/gpt-copy.git
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
Fine-tune which files are processed using include and exclude options.

- **Include Files (`-i` or `--include`):**
  Specify one or more glob patterns (with optional brace expansion) to include only matching files.

  **Examples:**
  - Include all Python files in the `src` folder:
    ```sh
    gpt-copy /path/to/directory -i "src/*.py"
    ```
  - Include specific modules:
    ```sh
    gpt-copy /path/to/directory -i "src/{module1,module2}.py"
    ```

- **Exclude Files (`-e` or `--exclude`):**
  Specify one or more glob patterns to exclude files. Exclusion takes precedence over inclusion.

  **Examples:**
  - Exclude all files in the `tests` folder:
    ```sh
    gpt-copy /path/to/directory -e "tests/*"
    ```
  - Exclude a specific file:
    ```sh
    gpt-copy /path/to/directory -i "src/*.py" -e "src/__init__.py"
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

**Explicitly enable line numbers (redundant, but supported for backward compatibility):**
```sh
gpt-copy /path/to/directory -n
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
