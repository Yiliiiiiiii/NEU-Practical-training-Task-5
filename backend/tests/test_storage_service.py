import hashlib

import pytest


def test_storage_service_writes_reads_json_and_hashes_file(tmp_path):
    from app.services.storage_service import StorageService

    service = StorageService(tmp_path)
    payload = {"doc_id": "doc_001", "title": "数据平台操作手册"}

    path = service.save_json("documents/doc_001/uir.json", payload)

    assert path == tmp_path / "documents" / "doc_001" / "uir.json"
    assert service.read_json("documents/doc_001/uir.json") == payload
    assert service.sha256("documents/doc_001/uir.json") == hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_storage_service_writes_and_reads_text(tmp_path):
    from app.services.storage_service import StorageService

    service = StorageService(tmp_path)

    service.write_text("tasks/task_001/content.md", "# 标题\n\n正文")

    assert service.read_text("tasks/task_001/content.md") == "# 标题\n\n正文"


def test_storage_service_rejects_unsafe_paths(tmp_path):
    from app.services.storage_service import StorageService

    service = StorageService(tmp_path)

    unsafe_paths = [
        "../outside.json",
        "documents/../../outside.json",
        "C:/outside.json",
        "/outside.json",
    ]

    for path in unsafe_paths:
        with pytest.raises(ValueError, match="unsafe storage path"):
            service.resolve(path)
