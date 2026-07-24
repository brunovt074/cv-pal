from __future__ import annotations

from typing import Protocol


class CheckpointStorePort(Protocol):
    """Caches the result of one expensive (LLM-backed) step by key, so a
    killed/interrupted pipeline run resumes instead of re-paying completed
    calls. See application/use_cases/build_knowledge_base.py.
    """

    def get(self, key: str) -> object | None: ...
    def set(self, key: str, value: object) -> None: ...
