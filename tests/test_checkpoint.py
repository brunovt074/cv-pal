from pydantic import BaseModel

from cvpal.analytics.checkpoint import with_checkpoint_list, with_checkpoint_raw


class _Thing(BaseModel):
    name: str
    value: int


def test_with_checkpoint_list_computes_and_writes_on_first_call(tmp_path):
    path = tmp_path / "things.json"
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="a", value=1)]

    result = with_checkpoint_list(path, _Thing, compute)
    assert result == [_Thing(name="a", value=1)]
    assert path.exists()
    assert len(calls) == 1


def test_with_checkpoint_list_reuses_existing_file_without_recomputing(tmp_path):
    path = tmp_path / "things.json"
    calls = []

    def compute():
        calls.append(1)
        return [_Thing(name="a", value=1)]

    with_checkpoint_list(path, _Thing, compute)
    result = with_checkpoint_list(path, _Thing, compute)

    assert result == [_Thing(name="a", value=1)]
    assert len(calls) == 1  # not called again


def test_with_checkpoint_raw_roundtrips_arbitrary_json(tmp_path):
    path = tmp_path / "raw.json"
    calls = []

    def compute():
        calls.append(1)
        return {"education": [{"institution": "X"}], "certifications": []}

    result = with_checkpoint_raw(path, compute)
    assert result["education"][0]["institution"] == "X"

    result2 = with_checkpoint_raw(path, compute)
    assert result2 == result
    assert len(calls) == 1
