from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app
from tests.topic5_helpers import announcement_convert_request


@pytest.fixture
def topic5_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
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


def test_topic5_convert_accepts_inline_config(topic5_client):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert", json=announcement_convert_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["schema_id"] == "announcement_doc"
    assert payload["template_id"] == "announcement_doc_base_v1"
    assert payload["content_json"]["data"]["title"] == "关于开展系统维护的公告"
    assert payload["content_json"]["data"]["issuer"] == "信息化办公室"
    assert payload["content_json"]["data"]["publish_date"] == "2026-07-09"
    assert payload["content_json"]["data"]["body"].startswith("为提升系统稳定性")
    assert payload["content_markdown"].startswith("# 关于开展系统维护的公告")
    assert payload["chunks"]
    assert payload["mapping_report"]["summary"]["input_mode"] == "inline_topic5_config"
    assert payload["content_organization_report"]["summary"]["chunk_count"] > 0
    assert payload["manifest"] is None
    assert payload["package_zip_path"] is None


def test_topic5_convert_package_creates_verified_package(topic5_client):
    client, _storage_root = topic5_client

    response = client.post("/api/v1/topic5/convert/package", json=announcement_convert_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["package_metadata"]["schema_id"] == "announcement_doc"
    assert payload["package_zip_path"]
    assert Path(payload["package_zip_path"]).is_file()
    assert payload["package_metadata"]["status"] == "completed"
    assert payload["verifier_report"]["passed"] is True
