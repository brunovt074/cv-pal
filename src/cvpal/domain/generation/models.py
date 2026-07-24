from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DocumentFormat(str, Enum):
    MARKDOWN = "markdown"
    DOCX = "docx"
    PDF = "pdf"


class TailoredDocument(BaseModel):
    """Output of the tailoring use case: a CV or cover letter generated
    from the knowledge base for one specific job posting.
    """

    kind: str
    company: str = ""
    role: str = ""
    language: str = "en"
    document_format: DocumentFormat = DocumentFormat.MARKDOWN
    content: str
    output_path: str | None = None
