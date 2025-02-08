# Concatenate Files

## Overview
This script recursively scans a directory, collects readable files, and concatenates them into a single structured stream. The output can be printed to stdout or written to a file. The purpose is to provide an easy way to feed structured content (such as codebases, documentation, or notes) into language models like GPT.

## Features
- Recursively scans directories while respecting `.gitignore` rules.
- Collects and concatenates all readable files.
- Identifies file types based on extensions and formats content accordingly.
- Excludes binary and ignored files.
- Outputs structured markdown with file-specific code fences.

## Installation
Ensure you have Python 3 installed. You can install dependencies using:

```sh
pip install -r requirements.txt
```

## Usage
### Basic Usage
```sh
python concatenate_files.py /path/to/directory
```

### Save Output to a File
```sh
python concatenate_files.py /path/to/directory -o output.md
```

## How It Works
1. **Collects `.gitignore` rules**
   - Scans the directory for `.gitignore` files and applies rules accordingly.
   - Ensures ignored files and directories are skipped.

2. **Generates a structured file tree**
   - Displays a visual representation of the directory structure.

3. **Reads and formats files**
   - Detects file type based on extension.
   - Wraps code files in proper markdown code fences.
   - Skips binary or unrecognized file types.

## Example Output
```
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

## File: `main.py`
*(Relative Path: `main.py`)*

```python
print("Hello, World!")
```

## File: `config.yaml`
*(Relative Path: `subdir/config.yaml`)*

```yaml
version: 1.0
enabled: true
```
```

## Contributing
If you'd like to contribute, feel free to open a pull request.

## License
This project is licensed under the MIT License.
