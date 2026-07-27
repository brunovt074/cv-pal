from cvpal.infrastructure.persistence.file_checkpoint_store import FileCheckpointStore


def test_get_returns_none_when_key_missing(tmp_path):
    store = FileCheckpointStore(tmp_path)
    assert store.get("missing") is None


def test_set_then_get_roundtrips_json(tmp_path):
    store = FileCheckpointStore(tmp_path)
    store.set("things", {"a": [1, 2, 3]})
    assert store.get("things") == {"a": [1, 2, 3]}


def test_set_creates_parent_directories(tmp_path):
    store = FileCheckpointStore(tmp_path / "nested" / "dir")
    store.set("things", {"ok": True})
    assert store.get("things") == {"ok": True}
