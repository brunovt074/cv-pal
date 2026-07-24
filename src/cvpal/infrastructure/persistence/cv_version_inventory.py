"""Deterministic (no agent) inventory of source CV documents.

One row per source file, grouped by "stack" (the top-level folder under
the CV root, e.g. Java/, PHP/, generic/), with the most-recently-modified
file in each stack flagged as the current variant. Used only by the
optional .xlsx export - the markdown knowledge base doesn't need per-file
provenance at this granularity.
"""

from __future__ import annotations

import os
from pathlib import Path

from cvpal.domain.documents.models import RawDocument
from cvpal.domain.knowledge.models import CVVersionEntry


def infer_stack(source_file: str) -> str:
    parts = Path(source_file).parts
    return parts[0] if len(parts) > 1 else "root"


def build_cv_versions(documents: list[RawDocument], raw_root: Path) -> list[CVVersionEntry]:
    cvs = [d for d in documents if d.doc_kind == "cv"]

    mtimes: dict[str, float] = {}
    for doc in cvs:
        full_path = raw_root / doc.source_file
        try:
            mtimes[doc.source_file] = os.path.getmtime(full_path)
        except OSError:
            mtimes[doc.source_file] = 0.0

    stacks: dict[str, list[str]] = {}
    for doc in cvs:
        stack = infer_stack(doc.source_file)
        stacks.setdefault(stack, []).append(doc.source_file)

    most_recent_per_stack = {
        stack: max(files, key=lambda f: mtimes[f]) for stack, files in stacks.items()
    }

    entries = []
    for doc in cvs:
        stack = infer_stack(doc.source_file)
        entries.append(
            CVVersionEntry(
                source_file=doc.source_file,
                stack=stack,
                source_language=doc.source_language,
                is_most_recent_variant=most_recent_per_stack[stack] == doc.source_file,
            )
        )
    return entries
