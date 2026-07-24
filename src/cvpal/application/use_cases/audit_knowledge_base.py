"""Surfaces personal-data fields with more than one distinct value across
the CV corpus (phone, linkedin, github, ...) - the ones
application/services/personal_data_resolution.py tags current/previous
during build. Read-only: this never changes the knowledge base, only
reports what a human should look at.
"""

from __future__ import annotations

from dataclasses import dataclass

from cvpal.domain.knowledge.models import KnowledgeBase


@dataclass(frozen=True)
class FieldInconsistency:
    field: str
    values: list[str]


def audit_personal_data(knowledge_base: KnowledgeBase) -> list[FieldInconsistency]:
    by_field: dict[str, list[str]] = {}
    for entry in knowledge_base.personal_data:
        by_field.setdefault(entry.field.strip().lower(), []).append(entry.value)

    return [
        FieldInconsistency(field=field, values=values)
        for field, values in sorted(by_field.items())
        if len(values) > 1
    ]
