from __future__ import annotations

from pathlib import Path

from odf import teletype
from odf.opendocument import load
from odf.table import Table, TableCell, TableRow
from odf.text import A, P


def _extract_hyperlinks(document) -> list[str]:
    """Plain-text extraction loses hyperlink targets (e.g. a "LinkedIn" link
    renders as the word "LinkedIn", not its URL) - the href lives on the
    anchor element, separate from teletype's text extraction.
    """
    urls: list[str] = []
    for anchor in document.getElementsByType(A):
        href = anchor.getAttribute("href")
        if href and href not in urls:
            urls.append(href)
    return urls


def extract_odt_text(path: Path) -> str:
    document = load(str(path))
    parts: list[str] = []

    for paragraph in document.getElementsByType(P):
        parts.append(teletype.extractText(paragraph))

    for table in document.getElementsByType(Table):
        for row in table.getElementsByType(TableRow):
            cells = row.getElementsByType(TableCell)
            parts.append(" | ".join(teletype.extractText(cell) for cell in cells))

    urls = _extract_hyperlinks(document)
    if urls:
        parts.append("")
        parts.append("Links:")
        parts.extend(urls)

    return "\n".join(parts)
