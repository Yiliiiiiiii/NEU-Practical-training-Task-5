import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_UIR = ROOT / "examples" / "production_like" / "uir" / "policy"


@pytest.fixture
def review_client(tmp_path) -> Iterator[TestClient]:
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
        yield client


def import_policy_document(client: TestClient, filename: str) -> str:
    uir = json.loads((PRODUCTION_UIR / filename).read_text(encoding="utf-8"))
    response = client.post("/api/v1/documents/import", json={"uir": uir})
    assert response.status_code == 200
    return response.json()["doc_id"]


def create_policy_task(
    client: TestClient,
    doc_id: str,
    options: dict | None = None,
) -> str:
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": doc_id,
            "schema_id": "policy_doc",
            "template_id": "policy_doc_base_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False, **(options or {})},
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def execute_task(client: TestClient, task_id: str) -> dict:
    response = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert response.status_code == 200
    return response.json()


def test_review_approve_candidate_pack_activation_affects_new_task(review_client):
    doc_id = import_policy_document(review_client, "policy_002_alias_variants.json")
    task_id = create_policy_task(review_client, doc_id)
    executed = execute_task(review_client, task_id)
    assert executed["status"] == "review_required"
    old_mapping_before_activation = review_client.get(
        f"/api/v1/tasks/{task_id}/reports/mapping"
    ).json()

    reviews = review_client.get("/api/v1/reviews", params={"status": "pending"})
    assert reviews.status_code == 200
    title_review = next(
        item
        for item in reviews.json()["items"]
        if item["source_field_name"] == "通知名称" and item["target_field_id"] == "title"
    )

    approve = review_client.post(
        f"/api/v1/reviews/{title_review['review_id']}/approve",
        json={
            "reviewer": "demo_user",
            "comment": "同意作为标题别名",
            "create_knowledge_candidate": True,
        },
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    candidates = review_client.get("/api/v1/knowledge/candidates")
    assert candidates.status_code == 200
    candidate = next(
        item
        for item in candidates.json()["items"]
        if item["alias"] == "通知名称" and item["target_field_id"] == "title"
    )
    assert candidate["status"] == "pending"

    accepted = review_client.post(
        f"/api/v1/knowledge/candidates/{candidate['candidate_id']}/accept"
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    draft_pack = review_client.post(
        "/api/v1/knowledge/packs",
        json={
            "schema_id": "policy_doc",
            "template_id": "policy_doc_base_v1",
            "name": "policy review aliases",
            "created_by": "demo_user",
        },
    )
    assert draft_pack.status_code == 200
    assert draft_pack.json()["status"] == "draft"

    draft_effective = review_client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "policy_doc", "template_id": "policy_doc_base_v1"},
    )
    assert draft_effective.status_code == 200
    assert "通知名称" not in draft_effective.json()["aliases"].get("title", [])

    active_pack = review_client.post(
        f"/api/v1/knowledge/packs/{draft_pack.json()['pack_id']}/activate"
    )
    assert active_pack.status_code == 200
    assert active_pack.json()["status"] == "active"

    active_effective = review_client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "policy_doc", "template_id": "policy_doc_base_v1"},
    )
    assert active_effective.status_code == 200
    assert "通知名称" in active_effective.json()["aliases"]["title"]

    new_task_id = create_policy_task(review_client, doc_id)
    execute_task(review_client, new_task_id)
    mapping = review_client.get(f"/api/v1/tasks/{new_task_id}/reports/mapping").json()
    assert any(
        item["source_field"]["source_name"] == "通知名称"
        and item["target_field_id"] == "title"
        and item["status"] == "confirmed"
        for item in mapping["mappings"]
    )

    old_mapping_after_activation = review_client.get(
        f"/api/v1/tasks/{task_id}/reports/mapping"
    ).json()
    assert old_mapping_after_activation == old_mapping_before_activation

    metrics = review_client.get("/api/v1/knowledge/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["active_packs"] == 1
    assert metrics.json()["accepted_candidates"] == 1


def test_reject_review_does_not_create_candidate(review_client):
    doc_id = import_policy_document(review_client, "policy_002_alias_variants.json")
    task_id = create_policy_task(review_client, doc_id)
    execute_task(review_client, task_id)

    review = review_client.get("/api/v1/reviews", params={"status": "pending"}).json()["items"][0]
    rejected = review_client.post(
        f"/api/v1/reviews/{review['review_id']}/reject",
        json={"reviewer": "demo_user", "comment": "语义不一致"},
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert review_client.get("/api/v1/knowledge/candidates").json()["items"] == []


def test_badcase_candidate_is_blocked(review_client):
    doc_id = import_policy_document(review_client, "policy_002_alias_variants.json")
    task_id = create_policy_task(
        review_client,
        doc_id,
        options={
            "badcases": [
                {
                    "source_field": "通知名称",
                    "forbidden_target_fields": ["title"],
                }
            ]
        },
    )
    execute_task(review_client, task_id)
    reviews = review_client.get("/api/v1/reviews", params={"status": "pending"}).json()["items"]
    title_review = next(item for item in reviews if item["source_field_name"] == "通知名称")

    approve = review_client.post(
        f"/api/v1/reviews/{title_review['review_id']}/approve",
        json={
            "reviewer": "demo_user",
            "comment": "badcase should block candidate",
            "create_knowledge_candidate": True,
        },
    )
    assert approve.status_code == 200

    candidate = review_client.get("/api/v1/knowledge/candidates").json()["items"][0]
    assert candidate["badcase_hit"] is True
    assert candidate["status"] == "blocked"

    accept = review_client.post(f"/api/v1/knowledge/candidates/{candidate['candidate_id']}/accept")
    assert accept.status_code == 400
