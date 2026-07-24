from __future__ import annotations

from pydantic import BaseModel, Field


class RawDocument(BaseModel):
    """Mechanical extraction output for a single source file.

    Section detection here is best-effort — the goal is to hand analytics a
    dict of plausible section-name -> raw text blobs, not a parsed CV.
    """

    source_file: str
    source_language: str = Field(default="unknown")
    doc_kind: str = Field(description='"cv" or "cover_letter", inferred from filename/path')
    sections: dict[str, str] = Field(default_factory=dict)
    unstructured: str | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
