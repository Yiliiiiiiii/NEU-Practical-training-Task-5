import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, ConversionTask, Document, ReviewRecord
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService


def add_review(
    db: Session,
    *,
    review_id: str,
    doc_id: str,
    schema_id: str,
    options: dict[str, object],
    created_at: datetime | None = None,
) -> None:
    db.add(
        Document(
            doc_id=doc_id,
            title=doc_id,
            uir_version="1.0",
            source_name=None,
            storage_path=f"{doc_id}.json",
            block_count=1,
            metadata_json=json.dumps({"doc_type": schema_id}, ensure_ascii=False),
        )
    )
    task_id = f"task_{review_id}"
    db.add(
        ConversionTask(
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema_id,
            schema_version="1.0.0",
            template_id=f"{schema_id}_base_v1",
            template_version="1.0.0",
            status="review_required",
            input_hash=review_id,
            options_json=json.dumps(options, ensure_ascii=False),
        )
    )
    db.add(
        ReviewRecord(
            review_id=review_id,
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema_id,
            template_id=f"{schema_id}_base_v1",
            mapping_id=f"mapping_{review_id}",
            candidate_id=f"candidate_{review_id}",
            source_field_name="发布日期",
            source_path="$.blocks.b1.text",
            target_field_id="publish_date",
            suggested_by="deterministic",
            confidence=0.7,
            reason="needs scoped review",
            status="pending",
            old_target_field_id=None,
            new_target_field_id="publish_date",
            decision="pending",
            comment=None,
            review_comment=None,
            reviewer="system",
            created_at=created_at or datetime.now(UTC),
            updated_at=created_at or datetime.now(UTC),
        )
    )


@pytest.fixture
def db_session(tmp_path) -> Session:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_reviews(db: Session) -> None:
    now = datetime.now(UTC)
    add_review(
        db,
        review_id="review_current_policy",
        doc_id="real_policy_001",
        schema_id="policy_doc",
        options={
            "run_id": "run_current",
            "dataset_id": "real_world_non_procurement_50",
            "dataset_split": "eval",
            "task_batch_id": "batch_current",
            "doc_type": "policy_doc",
        },
        created_at=now,
    )
    add_review(
        db,
        review_id="review_current_general",
        doc_id="real_general_001",
        schema_id="general_doc",
        options={
            "run_id": "run_current",
            "dataset_id": "real_world_non_procurement_50",
            "dataset_split": "eval",
            "task_batch_id": "batch_current",
            "doc_type": "general_doc",
        },
        created_at=now + timedelta(seconds=1),
    )
    add_review(
        db,
        review_id="review_historical",
        doc_id="phase_d_policy_001",
        schema_id="policy_doc",
        options={
            "run_id": "run_phase_d",
            "dataset_id": "phase_d_archive",
            "dataset_split": "eval",
            "task_batch_id": "batch_phase_d",
            "doc_type": "policy_doc",
        },
        created_at=now - timedelta(days=10),
    )
    add_review(
        db,
        review_id="review_procurement",
        doc_id="procurement_001",
        schema_id="procurement_doc",
        options={
            "run_id": "run_current",
            "dataset_id": "real_world_non_procurement_50",
            "dataset_split": "eval",
            "task_batch_id": "batch_current",
            "doc_type": "procurement_doc",
        },
        created_at=now,
    )
    db.commit()


def ids(records: list[ReviewRecord]) -> set[str]:
    return {record.review_id for record in records}


def test_default_scoped_query_requires_explicit_scope_and_does_not_read_history(
    db_session,
) -> None:
    seed_reviews(db_session)
    service = ReviewKnowledgeWorkflowService(db=db_session)

    with pytest.raises(ValueError, match="explicit review scope"):
        service.list_reviews(status="pending", include_historical=False)

    records = service.list_reviews(
        status="pending",
        dataset_id="real_world_non_procurement_50",
        include_historical=False,
    )

    assert "review_historical" not in ids(records)


def test_dataset_id_filter_limits_current_eval_scope(db_session) -> None:
    seed_reviews(db_session)
    service = ReviewKnowledgeWorkflowService(db=db_session)

    records = service.list_reviews(
        status="pending",
        dataset_id="real_world_non_procurement_50",
        include_historical=False,
    )

    assert ids(records) == {
        "review_current_policy",
        "review_current_general",
        "review_procurement",
    }


def test_doc_ids_filter_limits_reviews_to_explicit_documents(db_session) -> None:
    seed_reviews(db_session)
    service = ReviewKnowledgeWorkflowService(db=db_session)

    records = service.list_reviews(
        status="pending",
        doc_ids=["real_policy_001"],
        include_historical=False,
    )

    assert ids(records) == {"review_current_policy"}


def test_doc_type_filter_limits_reviews_to_schema_family(db_session) -> None:
    seed_reviews(db_session)
    service = ReviewKnowledgeWorkflowService(db=db_session)

    records = service.list_reviews(
        status="pending",
        dataset_id="real_world_non_procurement_50",
        doc_type="policy_doc",
        include_historical=False,
    )

    assert ids(records) == {"review_current_policy"}


def test_include_historical_true_allows_full_pending_queue(db_session) -> None:
    seed_reviews(db_session)
    service = ReviewKnowledgeWorkflowService(db=db_session)

    records = service.list_reviews(status="pending", include_historical=True)

    assert ids(records) == {
        "review_current_policy",
        "review_current_general",
        "review_historical",
        "review_procurement",
    }


def test_procurement_reviews_do_not_enter_non_procurement_scope(db_session) -> None:
    seed_reviews(db_session)
    service = ReviewKnowledgeWorkflowService(db=db_session)

    records = service.list_reviews(
        status="pending",
        dataset_id="real_world_non_procurement_50",
        doc_type="non_procurement",
        include_historical=False,
    )

    assert ids(records) == {"review_current_policy", "review_current_general"}
