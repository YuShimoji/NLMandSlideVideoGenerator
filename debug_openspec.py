#!/usr/bin/env python3
"""Debug OpenSpec parsing"""

import re
from pathlib import Path

def debug_parsing():
    spec_file = Path("docs/openspec_components.md")
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("File content length:", len(content))

    # Find openspec blocks
    spec_blocks = re.findall(r'```openspec(.*?)```', content, re.DOTALL)
    print(f">Found {len(spec_blocks)} spec blocks")

    for i, block in enumerate(spec_blocks):
        print(f"\nBlock {i+1}:")
        print(repr(block[:200]))

if __name__ == "__main__":
    debug_parsing()
