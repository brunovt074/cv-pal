from __future__ import annotations

from pathlib import Path

from odf import teletype
from odf.opendocument import load
from odf.table import Table, TableCell, TableRow
from odf.text import P


def extract_odt_text(path: Path) -> str:
    document = load(str(path))
    parts: list[str] = []

    for paragraph in document.getElementsByType(P):
        parts.append(teletype.extractText(paragraph))

    for table in document.getElementsByType(Table):
        for row in table.getElementsByType(TableRow):
            cells = row.getElementsByType(TableCell)
            parts.append(" | ".join(teletype.extractText(cell) for cell in cells))

    return "\n".join(parts)
