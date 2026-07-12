from __future__ import annotations

from pathlib import Path

import docx


def extract_docx_text(path: Path) -> str:
    document = docx.Document(str(path))
    parts: list[str] = []

    for para in document.paragraphs:
        parts.append(para.text)

    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))

    return "\n".join(parts)
