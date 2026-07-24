from __future__ import annotations

from typing import Protocol

from cvpal.domain.documents.models import RawDocument


class RawDocumentRepositoryPort(Protocol):
    """Reads/writes the intermediate ingestion dump (`data/ingested.json`)."""

    def load(self) -> list[RawDocument]: ...
    def save(self, documents: list[RawDocument]) -> None: ...
    def exists(self) -> bool: ...
