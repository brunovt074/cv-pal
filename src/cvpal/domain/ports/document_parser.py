from __future__ import annotations

from pathlib import Path
from typing import Protocol

from cvpal.domain.documents.models import RawDocument


class DocumentParserPort(Protocol):
    """Discovers source files under a root and extracts a RawDocument from
    each one, dispatching by format.
    """

    def discover(self, root: Path) -> list[Path]: ...
    def supports(self, path: Path) -> bool: ...
    def extract(self, path: Path, root: Path) -> RawDocument: ...
    def infer_doc_kind(self, path: Path) -> str: ...
