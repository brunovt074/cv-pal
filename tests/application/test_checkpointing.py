from pydantic import BaseModel

from cvpal.application.services.checkpointing import (
    fingerprint_text,
    with_checkpoint_list,
    with_checkpoint_raw,
)
from cvpal.infrastructure.persistence.file_checkpoint_store import FileCheckpointStore


class _Thing(BaseModel):
    name: str
    value: int


def test_with_checkpoint_list_computes_and_writes_on_first_call(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="a", value=1)]

    result, was_recomputed = with_checkpoint_list(store, "things", _Thing, "fp-1", compute)
    assert result == [_Thing(name="a", value=1)]
    assert was_recomputed is True
    assert store.get("things") is not None
    assert len(calls) == 1


def test_with_checkpoint_list_reuses_value_when_fingerprint_matches(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="a", value=1)]

    with_checkpoint_list(store, "things", _Thing, "fp-1", compute)
    result, was_recomputed = with_checkpoint_list(store, "things", _Thing, "fp-1", compute)

    assert result == [_Thing(name="a", value=1)]
    assert was_recomputed is False
    assert len(calls) == 1  # not called again


def test_with_checkpoint_list_recomputes_when_fingerprint_changes(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="a", value=len(calls))]

    with_checkpoint_list(store, "things", _Thing, "fp-1", compute)
    result, was_recomputed = with_checkpoint_list(store, "things", _Thing, "fp-2", compute)

    assert was_recomputed is True
    assert len(calls) == 2
    assert result == [_Thing(name="a", value=2)]


def test_with_checkpoint_list_treats_old_format_checkpoint_as_a_miss(tmp_path):
    store = FileCheckpointStore(tmp_path)
    store.set("things", [{"name": "stale", "value": 0}])  # pre-fingerprint format: a bare list
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="fresh", value=1)]

    result, was_recomputed = with_checkpoint_list(store, "things", _Thing, "fp-1", compute)
    assert was_recomputed is True
    assert result == [_Thing(name="fresh", value=1)]
    assert len(calls) == 1


def test_with_checkpoint_raw_roundtrips_arbitrary_json(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return {"education": [{"institution": "X"}], "certifications": []}

    result, was_recomputed = with_checkpoint_raw(store, "edu", "fp-1", compute)
    assert result["education"][0]["institution"] == "X"
    assert was_recomputed is True

    result2, was_recomputed2 = with_checkpoint_raw(store, "edu", "fp-1", compute)
    assert result2 == result
    assert was_recomputed2 is False
    assert len(calls) == 1


def test_with_checkpoint_raw_recomputes_when_fingerprint_changes(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return {"n": len(calls)}

    with_checkpoint_raw(store, "edu", "fp-1", compute)
    result, was_recomputed = with_checkpoint_raw(store, "edu", "fp-2", compute)

    assert was_recomputed is True
    assert result == {"n": 2}


def test_fingerprint_text_is_deterministic_and_sensitive_to_content():
    assert fingerprint_text("abc") == fingerprint_text("abc")
    assert fingerprint_text("abc") != fingerprint_text("abd")
