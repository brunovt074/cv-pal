from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pdfplumber

_MIN_ALPHA_RATIO = 0.5


def _alpha_ratio(text: str) -> float:
    """Fraction of alphabetic characters among non-whitespace characters.

    `layout=True` extraction preserves original PDF spacing, which can pad
    the text with large blank runs (wide margins, centered content) - those
    blanks must not count against the ratio, or well-formed PDFs get flagged
    as garbled.
    """
    non_whitespace = [c for c in text if not c.isspace()]
    if not non_whitespace:
        return 0.0
    alpha = sum(1 for c in non_whitespace if c.isalpha())
    return alpha / len(non_whitespace)


def _extract_hyperlinks(path: Path) -> list[str]:
    """Plain-text extraction loses hyperlink targets (e.g. a "LinkedIn" link
    renders as the word "LinkedIn", not its URL) - PDF hyperlinks are page
    annotations, separate from the text layer, so we pull them separately.
    """
    urls: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for link in page.hyperlinks:
                uri = link.get("uri")
                if uri and uri not in urls:
                    urls.append(uri)
    return urls


def _extract_with_pdfplumber(path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True) or ""
            parts.append(text)
    return "\n".join(parts)


def _extract_with_pdftotext(path: Path) -> str | None:
    if shutil.which("pdftotext") is None:
        return None
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode(errors="replace")


def _append_links(text: str, urls: list[str]) -> str:
    if not urls:
        return text
    return text + "\n\nLinks:\n" + "\n".join(urls)


def extract_pdf_text(path: Path) -> tuple[str, list[str]]:
    """Extract text from a PDF, falling back to `pdftotext -layout` if the
    pdfplumber output looks garbled (low alpha ratio among non-whitespace
    characters, e.g. scanned/corrupted PDFs). Hyperlink targets (LinkedIn,
    GitHub, project URLs) are appended as a "Links:" block since they live
    in page annotations, not the text layer either extractor reads.

    Returns (text, warnings).
    """
    warnings: list[str] = []
    urls = _extract_hyperlinks(path)
    text = _extract_with_pdfplumber(path)

    if _alpha_ratio(text) >= _MIN_ALPHA_RATIO:
        return _append_links(text, urls), warnings

    warnings.append("pdfplumber output looked garbled, falling back to pdftotext -layout")
    fallback_text = _extract_with_pdftotext(path)
    if fallback_text is not None and _alpha_ratio(fallback_text) >= _MIN_ALPHA_RATIO:
        return _append_links(fallback_text, urls), warnings

    warnings.append("pdftotext fallback also failed or unavailable; using raw pdfplumber output")
    return _append_links(text, urls), warnings
