"""Delete tailored CV/cover-letter outputs from data/outputs/.

Two modes:
- remove a single file by exact name (sanity-checked to stay inside
  data/outputs/, with a directory-traversal guard)
- wipe the whole outputs directory (--all)

This is a pure filesystem operation — no agent, no knowledge base, no
network. Kept in application/ (not infrastructure) because it is
policy-level (refuse to do anything if neither argument is supplied,
refuse paths that escape the outputs dir) rather than a low-level
adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CleanOutputsResult:
    deleted: list[Path]
    reason: str | None = None


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def clean_outputs(*, outputs_dir: Path, filename: str | None, remove_all: bool) -> CleanOutputsResult:
    if remove_all and filename:
        return CleanOutputsResult(
            deleted=[], reason="Pass either a file name or --all, not both."
        )
    if not remove_all and not filename:
        return CleanOutputsResult(
            deleted=[],
            reason="Pass a file name to delete, or --all/-a to wipe the outputs directory.",
        )

    outputs_dir.mkdir(parents=True, exist_ok=True)

    if remove_all:
        deleted = sorted(p for p in outputs_dir.iterdir() if p.is_file())
        for path in deleted:
            path.unlink()
        return CleanOutputsResult(deleted=deleted)

    target = (outputs_dir / filename).resolve()
    if not _is_inside(target, outputs_dir.resolve()):
        return CleanOutputsResult(
            deleted=[],
            reason=f"Refusing to delete '{filename}': path escapes data/outputs/.",
        )
    if not target.exists():
        return CleanOutputsResult(deleted=[], reason=f"File not found: {filename}")
    if not target.is_file():
        return CleanOutputsResult(deleted=[], reason=f"Not a regular file: {filename}")
    target.unlink()
    return CleanOutputsResult(deleted=[target])
