import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.services.storage_service import StorageService


@pytest.fixture()
def storage(tmp_path):
    return StorageService(tmp_path / "storage")


def test_failed_publish_preserves_previous_json(storage, monkeypatch):
    storage.save_json("tasks/t1/content.json", {"version": 1})

    def fail_replace(_source, _destination):
        raise OSError("publish failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="publish failed"):
        storage.save_json("tasks/t1/content.json", {"version": 2})

    assert storage.read_json("tasks/t1/content.json") == {"version": 1}
    assert list(storage.resolve("tasks/t1").glob("*.tmp")) == []


def test_failed_text_publish_preserves_previous_text(storage, monkeypatch):
    storage.write_text("tasks/t1/content.md", "version one")

    def fail_replace(_source, _destination):
        raise OSError("publish failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="publish failed"):
        storage.write_text("tasks/t1/content.md", "version two")

    assert storage.read_text("tasks/t1/content.md") == "version one"
    assert list(storage.resolve("tasks/t1").glob("*.tmp")) == []


def test_concurrent_json_writes_publish_one_complete_value(storage):
    values = [{"writer": index, "payload": "x" * 10_000} for index in range(8)]

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda value: storage.save_json("tasks/t1/content.json", value),
                values,
            )
        )

    raw = storage.resolve("tasks/t1/content.json").read_text(encoding="utf-8")
    assert json.loads(raw) in values
    assert list(storage.resolve("tasks/t1").glob("*.tmp")) == []
