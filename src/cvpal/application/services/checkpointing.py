"""Typed convenience over CheckpointStorePort - validates cached JSON back
into pydantic models, so use cases don't do it themselves.

Checkpoints are content-addressed, not existence-based: each entry stores
the fingerprint of the input that produced it alongside the result. A
checkpoint is only reused if the caller's current fingerprint matches -
this is what lets `build_knowledge_base` skip an agent call for a section
whose underlying CV content hasn't changed, and safely recompute only the
sections that did, instead of "does a checkpoint file exist" (which goes
stale the moment a CV is added/edited, and can't detect a partial change).
An old-format checkpoint (pre-fingerprint, or a mismatched fingerprint) is
treated as a cache miss, not an error - it's simply recomputed.
"""

from __future__ import annotations

import hashlib
from typing import Callable, TypeVar

from pydantic import BaseModel, TypeAdapter

from cvpal.domain.ports.checkpoint_store import CheckpointStorePort

T = TypeVar("T", bound=BaseModel)


def fingerprint_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def with_checkpoint_list(
    store: CheckpointStorePort,
    key: str,
    model_type: type[T],
    fingerprint: str,
    compute_fn: Callable[[], list[T]],
) -> tuple[list[T], bool]:
    """Returns (result, was_recomputed)."""
    cached = store.get(key)
    if isinstance(cached, dict) and cached.get("fingerprint") == fingerprint:
        return TypeAdapter(list[model_type]).validate_python(cached["result"]), False

    result = compute_fn()
    store.set(key, {"fingerprint": fingerprint, "result": [r.model_dump() for r in result]})
    return result, True


def with_checkpoint_raw(
    store: CheckpointStorePort, key: str, fingerprint: str, compute_fn: Callable[[], object]
) -> tuple[object, bool]:
    """For results that aren't a flat list of one model (e.g. an
    education/certifications pair) - caller handles (de)serialization.
    Returns (result, was_recomputed).
    """
    cached = store.get(key)
    if isinstance(cached, dict) and cached.get("fingerprint") == fingerprint:
        return cached["result"], False

    result = compute_fn()
    store.set(key, {"fingerprint": fingerprint, "result": result})
    return result, True
