# GPT Copy

## Overview
This script recursively scans a directory, collects readable files, and concatenates them into a single structured stream. The output can be printed to stdout or written to a file. The purpose is to provide an easy way to feed structured content (such as codebases, documentation, or notes) into language models like GPT.

## Features
- Recursively scans directories while respecting `.gitignore` rules.
- Collects and concatenates all readable files.
- Identifies file types based on extensions and formats content accordingly.
- Excludes binary and ignored files.
- Outputs structured markdown with file-specific code fences.
- Supports filtering files using glob-style include and exclude patterns.
- Includes a `tokens` CLI command to count the number of tokens in text using OpenAI's `tiktoken` library with the GPT-4o model encoding.

## Installation
Ensure you have Python 3 installed. You can install dependencies using:

```sh
pip install -r requirements.txt
```

Alternatively, install directly from Git:
```sh
pip install git+https://github.com/simone-viozzi/gpt-copy.git
```

## Usage

### Basic Usage
```sh
gpt-copy /path/to/directory
```

### Save Output to a File
```sh
gpt-copy /path/to/directory -o output.md
```

### Advanced File Filtering
You can fine-tune which files are processed using two new options:

- **Include Files (`-i` or `--include`):**
  Provide one or more glob patterns (with optional brace expansion) to specify files that should be **included**. When specified, only files matching at least one include pattern will be processed.

  **Examples:**
  - Include all Python files in the `src` folder:
    ```sh
    gpt-copy /path/to/directory -i "src/*.py"
    ```
  - Include specific modules using brace expansion:
    ```sh
    gpt-copy /path/to/directory -i "src/{module1,module2}.py"
    ```

- **Exclude Files (`-e` or `--exclude`):**
  Provide one or more glob patterns to specify files that should be **excluded**. Exclusion takes precedence over inclusion.

  **Examples:**
  - Exclude all files in the `tests` folder:
    ```sh
    gpt-copy /path/to/directory -e "tests/*"
    ```
  - Exclude a specific file even if it is included by another pattern:
    ```sh
    gpt-copy /path/to/directory -i "src/*.py" -e "src/__init__.py"
    ```

### Force Mode (`-f` or `--force`)
The `-f` (or `--force`) option forces the script to ignore `.gitignore` rules and Git-tracked file restrictions. This means the script will process **all** files in the provided directory regardless of any ignore settings.

**Usage Example:**
```sh
gpt-copy /path/to/directory -f
```

### Count Tokens with `tokens`
A new command, `tokens`, has been added to count the number of tokens in a given text using the `tiktoken` library with the GPT-4o model encoding. This command can read text from a file or from standard input, making it easy to pipe the output of `gpt-copy` into it.

**Examples:**
- Count tokens in a file:
  ```sh
  tokens file.txt
  ```
- Pipe the output of `gpt-copy` into `tokens`:
  ```sh
  gpt-copy /path/to/directory | tokens
  ```

## How It Works
1. **Collects `.gitignore` Rules**
   - Scans the directory for `.gitignore` files and applies rules accordingly.
   - Ensures ignored files and directories are skipped unless `-f` is specified.

2. **Generates a Structured File Tree**
   - Displays a visual representation of the directory structure.

3. **Reads and Formats Files**
   - Detects file type based on extension.
   - Wraps code files in proper markdown code fences.
   - Skips binary or unrecognized file types.

4. **Applies File Filtering**
   - **Include Patterns (`-i`):** Only files matching the specified patterns are processed.
   - **Exclude Patterns (`-e`):** Files matching these patterns are omitted—even if they match an include pattern.
   - The filtering is applied to file paths relative to the provided root directory.

## Example Output
````
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
````

## Contributing
If you'd like to contribute, feel free to open a pull request.

## License
This project is licensed under the MIT License.
