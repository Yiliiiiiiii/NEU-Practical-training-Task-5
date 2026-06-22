import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base, Document
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
DEMO_UIR = ROOT / "examples" / "demo" / "example_uir_general_doc.json"


@pytest.fixture
def documents_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_root = tmp_path / "storage"
    app = create_app(Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db"))

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client, storage_root


def load_demo_uir() -> dict:
    return json.loads(DEMO_UIR.read_text(encoding="utf-8"))


def test_import_document_writes_db_and_storage(documents_client):
    client, storage_root = documents_client
    uir = load_demo_uir()

    response = client.post("/api/v1/documents/import", json={"uir": uir})

    assert response.status_code == 200
    assert response.json() == {
        "doc_id": "doc_demo_general_001",
        "status": "imported",
        "block_count": 6,
    }
    assert (storage_root / "documents" / "doc_demo_general_001" / "uir.json").is_file()


def test_list_and_get_document_detail(documents_client):
    client, _storage_root = documents_client
    uir = load_demo_uir()

    client.post("/api/v1/documents/import", json={"uir": uir})
    list_response = client.get("/api/v1/documents")
    detail_response = client.get("/api/v1/documents/doc_demo_general_001")

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["title"] == "数据平台操作手册"
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["doc_id"] == "doc_demo_general_001"
    assert detail["metadata"]["文档标题"] == "数据平台操作手册"
    assert detail["blocks_preview"][0]["block_id"] == "blk_g_001"


def test_document_detail_returns_404_for_unknown_doc(documents_client):
    client, _storage_root = documents_client

    response = client.get("/api/v1/documents/missing_doc")

    assert response.status_code == 404
    assert response.json()["detail"] == "document not found"


def test_import_document_upserts_existing_record(documents_client):
    client, _storage_root = documents_client
    uir = load_demo_uir()

    first = client.post("/api/v1/documents/import", json={"uir": uir})
    second = client.post("/api/v1/documents/import", json={"uir": uir})

    assert first.status_code == 200
    assert second.status_code == 200

    from app.api.deps import get_db

    override = client.app.dependency_overrides[get_db]
    db = next(override())
    try:
        assert db.query(Document).count() == 1
    finally:
        db.close()
