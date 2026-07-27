"""File-backed CheckpointStorePort.

Each structuring call shells out to an agent and can take long enough that
a single process running the whole pipeline risks being killed by an
external time limit before it finishes. Checkpointing each step's raw
result to disk lets the pipeline be re-run in short bursts, resuming from
whatever already completed instead of losing all prior work.
"""

from __future__ import annotations

import json
from pathlib import Path


class FileCheckpointStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _path(self, key: str) -> Path:
        return self._base_dir / f"{key}.json"

    def get(self, key: str) -> object | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def set(self, key: str, value: object) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False))
