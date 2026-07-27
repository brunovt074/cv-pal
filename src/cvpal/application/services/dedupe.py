"""Mechanical (non-LLM) deduplication of raw section text across CV versions.

The same role/summary/skill line is repeated near-verbatim across dozens of
source files. Collapsing exact/near-exact duplicates here - before any LLM
call - shrinks the input volume the structuring pass has to reason over, and
is cheap and fully deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from cvpal.application.services.checkpointing import fingerprint_text
from cvpal.domain.documents.models import RawDocument


@dataclass
class DedupedBlock:
    text: str
    source_files: list[str] = field(default_factory=list)


def _normalize_for_hashing(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def dedupe_section_lines(documents: list[RawDocument], section: str) -> list[DedupedBlock]:
    """Collapse near-duplicate lines/bullets within one canonical section
    (e.g. "experience") across all documents, preserving provenance.

    Splits each document's section text into non-empty lines (a reasonable
    proxy for "bullet" given the corpus's bullet-per-line convention), then
    groups lines by normalized text.
    """
    blocks: dict[str, DedupedBlock] = {}

    for doc in documents:
        text = doc.sections.get(section)
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip().lstrip("•-*").strip()
            if not line:
                continue
            key = _normalize_for_hashing(line)
            if key in blocks:
                if doc.source_file not in blocks[key].source_files:
                    blocks[key].source_files.append(doc.source_file)
            else:
                blocks[key] = DedupedBlock(text=line, source_files=[doc.source_file])

    return list(blocks.values())


def dedupe_all_sections(
    documents: list[RawDocument], sections: list[str]
) -> dict[str, list[DedupedBlock]]:
    return {section: dedupe_section_lines(documents, section) for section in sections}


def fingerprint_blocks(blocks: list[DedupedBlock]) -> str:
    """Deterministic fingerprint of a section's deduped input - order of
    `blocks` doesn't affect it, only their content, so it's stable across
    runs regardless of dict-iteration order upstream.
    """
    normalized = "\n".join(
        f"{b.text}|{','.join(sorted(b.source_files))}"
        for b in sorted(blocks, key=lambda b: b.text)
    )
    return fingerprint_text(normalized)
