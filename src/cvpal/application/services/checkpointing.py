"""Typed convenience over CheckpointStorePort - validates cached JSON back
into pydantic models, so use cases don't do it themselves.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from pydantic import BaseModel, TypeAdapter

from cvpal.domain.ports.checkpoint_store import CheckpointStorePort

T = TypeVar("T", bound=BaseModel)


def with_checkpoint_list(
    store: CheckpointStorePort, key: str, model_type: type[T], compute_fn: Callable[[], list[T]]
) -> list[T]:
    cached = store.get(key)
    if cached is not None:
        return TypeAdapter(list[model_type]).validate_python(cached)

    result = compute_fn()
    store.set(key, [r.model_dump() for r in result])
    return result


def with_checkpoint_raw(
    store: CheckpointStorePort, key: str, compute_fn: Callable[[], object]
) -> object:
    """For results that aren't a flat list of one model (e.g. an
    education/certifications pair) - caller handles (de)serialization.
    """
    cached = store.get(key)
    if cached is not None:
        return cached

    result = compute_fn()
    store.set(key, result)
    return result
