from __future__ import annotations

from typing import Protocol

from cvpal.domain.knowledge.models import KnowledgeBase


class KnowledgeRepositoryPort(Protocol):
    """Reads/writes the knowledge base.

    Implemented by `infrastructure.persistence.markdown_knowledge_repository`
    against `data/knowledge-base.md` — the format both a human and any agent
    can edit directly, converging back through the same `save()`.
    """

    def load(self) -> KnowledgeBase: ...
    def save(self, knowledge_base: KnowledgeBase) -> None: ...
