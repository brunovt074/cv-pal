"""Lets an agent (or a human, via the same MCP tool) edit the knowledge
base directly - the markdown table parser is deliberately tolerant of
hand edits, which also means "does it parse" is not a strong enough
safety check on its own: garbage input still parses, just into a mostly
empty KnowledgeBase. This guards against that specific failure mode - an
accidental near-total wipe - without rejecting legitimate edits (adding a
project, tweaking a bullet, trimming a stale skill).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cvpal.domain.knowledge.models import KnowledgeBase

MIN_RETENTION_RATIO = 0.5


def _record_count(kb: KnowledgeBase) -> int:
    return (
        len(kb.personal_data)
        + len(kb.summaries)
        + len(kb.experience)
        + len(kb.education)
        + len(kb.certifications)
        + len(kb.skills)
        + len(kb.projects)
        + len(kb.languages)
    )


@dataclass(frozen=True)
class UpdateResult:
    accepted: bool
    reason: str
    knowledge_base: KnowledgeBase | None = None


def update_knowledge_base(
    current: KnowledgeBase,
    new_markdown: str,
    parse_markdown: Callable[[str], KnowledgeBase],
    *,
    force: bool = False,
) -> UpdateResult:
    new_kb = parse_markdown(new_markdown)
    old_count = _record_count(current)
    new_count = _record_count(new_kb)

    if old_count > 0 and not force and new_count < old_count * MIN_RETENTION_RATIO:
        return UpdateResult(
            accepted=False,
            reason=(
                f"New content has {new_count} records vs {old_count} currently - this looks "
                "like an accidental near-total wipe rather than an edit. If this is "
                "intentional, retry with force=True."
            ),
        )

    return UpdateResult(accepted=True, reason="ok", knowledge_base=new_kb)
