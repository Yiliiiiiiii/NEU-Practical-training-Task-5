import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import (
    Base,
    KnowledgePackItemRecord,
    KnowledgePackRecord,
    ReviewRecord,
)
from app.main import create_app


@pytest.fixture
def workbench_client(tmp_path) -> Iterator[tuple[TestClient, object]]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = session_factory()
    storage_root = tmp_path / "storage"
    app = create_app(Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db"))

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)
    with TestClient(app) as client:
        yield client, session
    session.close()


def add_review(
    session,
    review_id: str,
    *,
    source_label: str = "发文单位",
    target_field: str = "issuer",
    reason: str = "low confidence",
) -> None:
    session.add(
        ReviewRecord(
            review_id=review_id,
            task_id=f"task_{review_id}",
            doc_id=f"doc_{review_id}",
            schema_id="policy_doc",
            template_id="policy_doc_base_v1",
            mapping_id=f"mapping_{review_id}",
            source_field_name=source_label,
            source_path="blocks[0].text",
            target_field_id=target_field,
            suggested_by="fuzzy",
            confidence=0.62,
            reason=reason,
            status="pending",
            decision="pending",
            reviewer="system",
        )
    )
    session.commit()


def add_pack(
    session,
    pack_id: str,
    *,
    status: str,
    alias: str,
    target_field: str,
) -> None:
    session.add(
        KnowledgePackRecord(
            pack_id=pack_id,
            name=pack_id,
            schema_id="policy_doc",
            template_id="policy_doc_base_v1",
            version="1.0.0",
            status=status,
            created_by="test",
        )
    )
    session.add(
        KnowledgePackItemRecord(
            item_id=f"{pack_id}_item",
            pack_id=pack_id,
            item_type="alias",
            target_field_id=target_field,
            value_json=json.dumps({"alias": alias}, ensure_ascii=False),
        )
    )
    session.commit()


def test_review_summary_grouping_and_impact_preview(workbench_client) -> None:
    client, session = workbench_client
    add_review(session, "r1")
    add_review(session, "r2")

    summary = client.get("/api/v1/reviews/summary")
    assert summary.status_code == 200
    assert summary.json()["pending"] == 2

    grouped = client.get("/api/v1/reviews/grouped", params={"group_by": "source_label"})
    assert grouped.status_code == 200
    assert grouped.json()["items"][0]["count"] == 2

    impact = client.post("/api/v1/reviews/r1/impact-preview")
    assert impact.status_code == 200
    assert len(impact.json()["would_affect"]) == 1


def test_batch_safety_and_rejection_negative_knowledge(workbench_client) -> None:
    client, session = workbench_client
    add_review(
        session,
        "r1",
        source_label="控制价",
        target_field="award_amount",
        reason="risk_flags=control_price_not_award_amount",
    )
    add_review(
        session,
        "r2",
        source_label="控制价",
        target_field="award_amount",
        reason="risk_flags=control_price_not_award_amount",
    )

    unsafe = client.post(
        "/api/v1/reviews/batch-approve",
        json={"review_ids": ["r1", "r2"], "reviewer": "demo_user"},
    )
    assert unsafe.status_code == 400

    rejected = client.post(
        "/api/v1/reviews/batch-reject",
        json={
            "review_ids": ["r1", "r2"],
            "reviewer": "demo_user",
            "comment": "控制价不是中标金额",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["negative_rule_count"] == 2
    assert client.get("/api/v1/reviews/summary").json()["negative_rule_count"] == 1


def test_pack_governance_endpoints_and_rollback(workbench_client) -> None:
    client, session = workbench_client
    add_pack(session, "pack_a", status="active", alias="发文单位", target_field="issuer")
    add_pack(session, "pack_b", status="active", alias="发文单位", target_field="publisher")

    conflicts = client.get("/api/v1/knowledge/conflicts")
    assert conflicts.status_code == 200
    assert conflicts.json()["total"] == 1

    diff = client.get("/api/v1/knowledge/packs/pack_a/diff")
    assert diff.status_code == 200
    impact = client.get("/api/v1/knowledge/packs/pack_a/impact")
    assert impact.status_code == 200
    assert impact.json()["old_snapshot_unchanged"] is True

    rollback = client.post("/api/v1/knowledge/packs/pack_a/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "archived"
    assert rollback.json()["future_tasks_use_pack"] is False


def test_negative_knowledge_blocks_pack_activation_api(workbench_client) -> None:
    client, session = workbench_client
    add_review(
        session,
        "r1",
        source_label="控制价",
        target_field="award_amount",
    )
    client.post(
        "/api/v1/reviews/batch-reject",
        json={
            "review_ids": ["r1"],
            "reviewer": "demo_user",
            "comment": "控制价不是中标金额",
        },
    )
    add_pack(
        session,
        "pack_draft",
        status="draft",
        alias="控制价",
        target_field="award_amount",
    )

    activate = client.post("/api/v1/knowledge/packs/pack_draft/activate")

    assert activate.status_code == 400
    assert "negative knowledge" in activate.json()["detail"]
