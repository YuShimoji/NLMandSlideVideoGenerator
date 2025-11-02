#!/usr/bin/env python3
"""Simple file reader"""

from pathlib import Path

def read_file():
    spec_file = Path("docs/openspec_components.md")
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Content length:", len(content))
    print("First 500 chars:")
    print(repr(content[:500]))

if __name__ == "__main__":
    read_file()
