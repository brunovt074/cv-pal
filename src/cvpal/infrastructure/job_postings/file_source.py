from __future__ import annotations

from pathlib import Path

from cvpal.domain.jobs.models import JobPosting
from cvpal.infrastructure.parsers.docx_extractor import extract_docx_text

_TEXT_EXTENSIONS = {".txt", ".md"}


class FileJobPostingSource:
    """A job posting read from a local file - .txt/.md as plain text,
    .docx via the same extractor used for the CV corpus.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> JobPosting:
        suffix = self._path.suffix.lower()
        if suffix == ".docx":
            text = extract_docx_text(self._path)
        elif suffix in _TEXT_EXTENSIONS:
            text = self._path.read_text()
        else:
            raise ValueError(f"Unsupported job posting file extension: {suffix}")
        return JobPosting(source=str(self._path), raw_text=text.strip())
