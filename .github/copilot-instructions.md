# GPT Copy - Python CLI Tool

GPT Copy is a command-line tool that recursively scans directories and concatenates readable files into structured markdown output. This tool is designed to help developers easily feed codebases into language models like GPT.

## Project Overview

GPT Copy provides two main commands:
- `gpt-copy`: Scans directories and outputs structured markdown with file contents
- `tokens`: Counts tokens in text using OpenAI's tiktoken library

The tool respects `.gitignore` rules, supports file filtering with glob patterns, and includes features like line numbering, token counting, and tree structure visualization.

## Technology Stack

- **Python 3.10+**: Core language
- **Click**: Command-line interface framework
- **pathspec**: Gitignore pattern matching
- **tqdm**: Progress bars and status indicators
- **pygit2**: Git repository operations
- **tiktoken**: OpenAI token counting
- **pytest**: Testing framework
- **ruff**: Linting and code formatting
- **pre-commit**: Git hooks for code quality

## Architecture and Code Organization

### Core Modules

- **`gpt_copy.py`**: Main CLI command and directory scanning logic
- **`filter.py`**: File filtering, gitignore handling, and pattern matching
- **`tokens.py`**: Token counting functionality using tiktoken
- **`__init__.py`**: Package initialization and version management

### Design Principles

1. **Modular Design**: Separate concerns into focused modules
2. **CLI-First**: All functionality accessible via command-line interface
3. **Git Integration**: Respect Git ignore patterns and track file status
4. **Performance**: Use generators and streaming for large directories
5. **User Experience**: Provide clear progress indicators and helpful output

## Coding Standards and Conventions

### Python Style
- Follow PEP 8 standards enforced by ruff
- Use type hints for function parameters and return values
- Prefer descriptive variable names over comments
- Use docstrings for all public functions and classes
- Maximum line length of 88 characters (Black default)

### Error Handling
- Use specific exception types rather than bare `except`
- Provide meaningful error messages to users
- Handle file system errors gracefully (permissions, missing files)
- Log errors appropriately for debugging

### Testing
- Write unit tests for all core functionality
- Use pytest fixtures for test setup
- Test edge cases and error conditions
- Maintain high test coverage for critical paths

### CLI Design
- Use Click for all command-line interfaces
- Provide helpful help text and examples
- Support both short and long option names
- Validate input parameters early and clearly

## File Processing Guidelines

### Gitignore Handling
- Always respect `.gitignore` files unless `--force` is specified
- Collect gitignore patterns from all parent directories
- Use pathspec library for consistent pattern matching
- Handle nested gitignore files correctly

### File Type Detection
- Detect file types based on extensions
- Skip binary files automatically
- Provide appropriate code fence languages for markdown output
- Handle edge cases like files without extensions

### Output Formatting
- Generate clean, readable markdown structure
- Include file paths and metadata
- Add line numbers by default (configurable)
- Use consistent indentation and spacing

## Performance Considerations

### Memory Management
- Use generators for large file processing
- Stream file contents rather than loading all into memory
- Handle large directories efficiently
- Provide progress indicators for long operations

### File System Operations
- Minimize file system calls
- Cache directory traversal results when appropriate
- Handle symlinks and special files safely
- Respect system limits and permissions

## Integration Patterns

### Git Integration
- Use pygit2 for Git operations when available
- Fall back gracefully when not in a Git repository
- Handle Git errors (corrupt repos, missing objects)
- Respect Git's file status (tracked, ignored, etc.)

### Token Counting
- Use tiktoken for accurate OpenAI token counting
- Handle encoding errors gracefully
- Provide token statistics per file and total
- Support filtering by token count

## Development Workflow

### Before Implementation
- Run existing tests: `python -m pytest`
- Check code style: `ruff check .`
- Format code: `ruff format .`
- Verify type hints with mypy if available

### Code Review Checklist
- Does the code follow existing patterns?
- Are error cases handled appropriately?
- Is the functionality tested?
- Does it integrate well with the CLI interface?
- Is the documentation updated if needed?

## Best Practices for AI-Generated Code

When generating code for this project:

1. **Maintain Consistency**: Follow existing patterns in the codebase
2. **Handle Errors**: Always consider what could go wrong and handle it
3. **Test Coverage**: Include basic tests for new functionality
4. **Documentation**: Add docstrings and update help text as needed
5. **Performance**: Consider memory usage and file system efficiency
6. **User Experience**: Provide clear feedback and progress indicators

## Common Patterns

### CLI Command Structure
```python
@click.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--option', '-o', help='Option description')
def command_name(directory, option):
    """Command description."""
    # Implementation
```

### File Processing Loop
```python
for file_path in files:
    try:
        # Process file
        yield result
    except (IOError, OSError) as e:
        # Handle file system errors
        continue
```

### Progress Indicators
```python
from tqdm import tqdm

with tqdm(total=len(files), desc="Processing") as pbar:
    for file in files:
        # Process file
        pbar.update(1)
```

This project emphasizes clean, maintainable code that provides a reliable tool for developers working with language models.