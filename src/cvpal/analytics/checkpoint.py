"""Per-step checkpointing for the analytics pipeline.

Each structuring call shells out to an LLM and can take long enough that a
single process running the whole pipeline risks being killed by an external
time limit before it finishes. Checkpointing each step's result to disk lets
the pipeline be re-run in short bursts, resuming from whatever already
completed instead of losing all prior work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, TypeAdapter

T = TypeVar("T", bound=BaseModel)


def with_checkpoint_list(
    path: Path, model_type: type[T], compute_fn: Callable[[], list[T]]
) -> list[T]:
    if path.exists():
        data = json.loads(path.read_text())
        return TypeAdapter(list[model_type]).validate_python(data)

    result = compute_fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([r.model_dump() for r in result], indent=2, ensure_ascii=False)
    )
    return result


def with_checkpoint_raw(path: Path, compute_fn: Callable[[], object]) -> object:
    """For results that aren't a flat list of one model (e.g. the
    education/certifications tuple) - caller handles (de)serialization."""
    if path.exists():
        return json.loads(path.read_text())

    result = compute_fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result
