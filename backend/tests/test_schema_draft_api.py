from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app


@pytest.fixture
def schema_draft_client(tmp_path) -> Iterator[tuple[TestClient, Path]]:
    from app.api.deps import get_db, get_settings, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    storage_root = tmp_path / "storage"
    settings = Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db")
    app = create_app(settings)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client, storage_root


def sample_documents() -> list[dict]:
    return [
        {
            "uir_version": "1.0",
            "doc_id": f"draft_sample_{index}",
            "source": {"source_type": "external_uir", "source_name": "test"},
            "metadata": {"title": f"Draft sample {index}"},
            "blocks": [
                {
                    "block_id": "b001",
                    "type": "table",
                    "attributes": {
                        "rows": [
                            ["项目名称", f"Project {index}"],
                            ["预算金额", f"{index + 1}00万元"],
                        ]
                    },
                },
                {
                    "block_id": "b002",
                    "type": "paragraph",
                    "text": f"会议时间：2026年7月{index + 1}日",
                    "attributes": {},
                },
            ],
            "assets": [],
        }
        for index in range(5)
    ]


def test_discover_fields_from_sample_documents(schema_draft_client) -> None:
    client, _storage_root = schema_draft_client

    response = client.post(
        "/api/v1/schema-drafts/discover",
        json={"documents": sample_documents()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sample_count"] == 5
    assert any(item["field_name"] == "project_name" for item in body["field_candidates"])
    assert all(item["evidence_paths"] for item in body["field_candidates"])
    assert body["llm_auto_accepted_count"] == 0


def test_generate_get_validate_and_export_draft(schema_draft_client) -> None:
    client, storage_root = schema_draft_client

    generated = client.post(
        "/api/v1/schema-drafts/generate",
        json={
            "documents": sample_documents(),
            "schema_id": "project_notice_doc",
            "schema_name": "Project Notice Draft",
            "template_id": "project_notice_doc_draft_v1",
        },
    )

    assert generated.status_code == 200
    package = generated.json()
    draft_id = package["draft_id"]
    assert package["status"] == "draft"
    assert package["must_not_auto_activate"] is True
    assert package["risk_report"]["must_not_auto_activate"] is True
    assert package["draft_report"]["llm_auto_accepted_count"] == 0

    fetched = client.get(f"/api/v1/schema-drafts/{draft_id}")
    assert fetched.status_code == 200
    assert fetched.json()["draft_id"] == draft_id

    validated = client.post(f"/api/v1/schema-drafts/{draft_id}/validate")
    assert validated.status_code == 200
    assert validated.json()["must_not_auto_activate"] is True

    exported = client.post(f"/api/v1/schema-drafts/{draft_id}/export")
    assert exported.status_code == 200
    files = exported.json()["files"]
    assert set(files) == {
        "draft_schema",
        "draft_template",
        "draft_report",
        "risk_report",
    }
    assert all((storage_root / path).is_file() for path in files.values())

    schemas = client.get("/api/v1/schemas").json()["items"]
    assert all(item["schema_id"] != "project_notice_doc" for item in schemas)
    assert client.post(f"/api/v1/schema-drafts/{draft_id}/activate").status_code == 404
