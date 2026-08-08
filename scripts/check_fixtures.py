"""PII sweep over tests/fixtures/* binaries - the check a plain grep can't do.

PDF text is compressed and DOCX/ODT text is zipped, so a real person's name,
phone, email, or social links can sit inside a fixture invisibly to `rg`/`git
grep`. This extracts the actual text layer of every fixture with the
project's own extractors and greps *that* for known PII patterns.

The patterns themselves are real personal data, so they live outside version
control: put one regex per line in `scripts/pii_patterns.local` (gitignored,
see `scripts/pii_patterns.local.example`), or point `CVPAL_PII_PATTERNS_FILE`
at another path. Blank lines and `#` comments are ignored.

The sweep fails closed: with no patterns available it exits non-zero rather
than reporting a clean run it never performed.

Run before every commit that touches tests/fixtures/, and as part of the
pre-publish exit gate.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from cvpal.infrastructure.parsers.docx_extractor import extract_docx_text
from cvpal.infrastructure.parsers.odt_extractor import extract_odt_text
from cvpal.infrastructure.parsers.pdf_extractor import extract_pdf_text

SCRIPTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = SCRIPTS_DIR.parent / "tests" / "fixtures"
DEFAULT_PATTERNS_FILE = SCRIPTS_DIR / "pii_patterns.local"


def _patterns_file() -> Path:
    override = os.environ.get("CVPAL_PII_PATTERNS_FILE")
    return Path(override) if override else DEFAULT_PATTERNS_FILE


def _load_patterns(path: Path) -> list[str]:
    patterns = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _compile_pattern(patterns: list[str]) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


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
    path = _patterns_file()

    if not path.is_file():
        print(
            f"No PII pattern file at {path}.\n"
            f"Copy {SCRIPTS_DIR / 'pii_patterns.local.example'} to "
            f"{DEFAULT_PATTERNS_FILE} and fill in the values to screen for, "
            f"or set CVPAL_PII_PATTERNS_FILE to another path.\n"
            "Refusing to report a clean sweep that never ran.",
            file=sys.stderr,
        )
        return 2

    patterns = _load_patterns(path)
    if not patterns:
        print(f"{path} has no usable patterns.", file=sys.stderr)
        return 2

    pii_pattern = _compile_pattern(patterns)

    hits: list[str] = []
    for fixture in sorted(FIXTURES_DIR.iterdir()):
        if not fixture.is_file():
            continue
        text = _extract_text(fixture)
        for match in pii_pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            hits.append(f"{fixture.name}:{line_no}: {match.group(0)!r}")

    if hits:
        print("PII found in binary fixtures:", file=sys.stderr)
        for hit in hits:
            print(f"  {hit}", file=sys.stderr)
        return 1

    checked = sum(1 for p in FIXTURES_DIR.iterdir() if p.is_file())
    print(f"Checked {checked} fixtures against {len(patterns)} patterns, no PII found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
