#!/usr/bin/env python3
import sys
import click
import tiktoken
from pathlib import Path


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in the given text using tiktoken with the GPT-4o model encoding.
    """
    enc = tiktoken.encoding_for_model("gpt-4o")
    tokens = enc.encode(text)
    return len(tokens)


@click.command()
@click.argument(
    "input_file", type=click.Path(exists=True, dir_okay=False), required=False
)
def main(input_file: Path):
    """
    Count the tokens in the provided text.

    If INPUT_FILE is provided, the text is read from that file.
    Otherwise, the text is read from standard input.

    Examples:
      cat file.txt | tokens
      tokens file.txt
    """
    if input_file:
        with open(input_file, encoding="utf-8") as f:
            text = f.read()
    else:
        # Read from standard input (for piped input)
        text = sys.stdin.read()

    token_count = count_tokens(text)
    click.echo(f"Token count: {token_count}")
