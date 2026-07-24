from pydantic import BaseModel

from cvpal.application.services.checkpointing import with_checkpoint_list, with_checkpoint_raw
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

    result = with_checkpoint_list(store, "things", _Thing, compute)
    assert result == [_Thing(name="a", value=1)]
    assert store.get("things") is not None
    assert len(calls) == 1


def test_with_checkpoint_list_reuses_existing_value_without_recomputing(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="a", value=1)]

    with_checkpoint_list(store, "things", _Thing, compute)
    result = with_checkpoint_list(store, "things", _Thing, compute)

    assert result == [_Thing(name="a", value=1)]
    assert len(calls) == 1  # not called again


def test_with_checkpoint_raw_roundtrips_arbitrary_json(tmp_path):
    store = FileCheckpointStore(tmp_path)
    calls = []

    def compute():
        calls.append(1)
        return {"education": [{"institution": "X"}], "certifications": []}

    result = with_checkpoint_raw(store, "edu", compute)
    assert result["education"][0]["institution"] == "X"

    result2 = with_checkpoint_raw(store, "edu", compute)
    assert result2 == result
    assert len(calls) == 1
