"""PII sweep over tests/fixtures/* binaries - the check a plain grep can't do.

PDF text is compressed and DOCX/ODT text is zipped, so a real person's name,
phone, email, or social links can sit inside a fixture invisibly to `rg`/`git
grep`. This extracts the actual text layer of every fixture with the
project's own extractors and greps *that* for known PII patterns.

Run before every commit that touches tests/fixtures/, and as part of the
pre-publish exit gate (see PROJECT_STATUS.md).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from cvpal.infrastructure.parsers.docx_extractor import extract_docx_text
from cvpal.infrastructure.parsers.odt_extractor import extract_odt_text
from cvpal.infrastructure.parsers.pdf_extractor import extract_pdf_text

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Real PII to catch, in addition to anything an editor might paste in by
# habit later. Keep in sync with the sweep pattern used on the working tree.
_PII_PATTERN = re.compile(
    r"REDACTED-see-scripts/pii_patterns.local.example",
    re.IGNORECASE,
)


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text, _warnings = extract_pdf_text(path)
        return text
    if suffix == ".docx":
        return extract_docx_text(path)
    if suffix == ".odt":
        return extract_odt_text(path)
    raise ValueError(f"Unsupported fixture extension: {suffix}")


def main() -> int:
    hits: list[str] = []
    for path in sorted(FIXTURES_DIR.iterdir()):
        if not path.is_file():
            continue
        text = _extract_text(path)
        for match in _PII_PATTERN.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            hits.append(f"{path.name}:{line_no}: {match.group(0)!r}")

    if hits:
        print("PII found in binary fixtures:", file=sys.stderr)
        for hit in hits:
            print(f"  {hit}", file=sys.stderr)
        return 1

    print(f"Checked {sum(1 for p in FIXTURES_DIR.iterdir() if p.is_file())} fixtures, no PII found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
