"""Extracts a `<!-- cvpal:section=KEY --> ... <!-- /cvpal:section -->` block
from a rendered knowledge-base markdown document. Pure text processing, no
I/O - shared by the markdown repository (parsing the file back into domain
models) and the MCP server (serving a single section's raw text without
the whole document).
"""

from __future__ import annotations

import re


def extract_section_block(markdown: str, key: str) -> str | None:
    pattern = rf"<!-- cvpal:section={re.escape(key)} -->(.*?)<!-- /cvpal:section -->"
    match = re.search(pattern, markdown, re.DOTALL)
    return match.group(1) if match else None
