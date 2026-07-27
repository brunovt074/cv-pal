from __future__ import annotations

import json
from pathlib import Path

from cvpal.domain.documents.models import RawDocument


class JsonRawDocumentRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> list[RawDocument]:
        return [RawDocument(**d) for d in json.loads(self._path.read_text())]

    def save(self, documents: list[RawDocument]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([doc.model_dump() for doc in documents], indent=2, ensure_ascii=False)
        )
