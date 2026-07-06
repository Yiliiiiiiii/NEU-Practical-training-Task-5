import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, ReviewRecord
from app.services.review_workbench_service import ReviewWorkbenchService
from app.services.storage_service import StorageService


def make_service(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'review.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    return session, ReviewWorkbenchService(session, StorageService(tmp_path / "storage"))


def add_review(
    session,
    *,
    review_id: str,
    source_label: str,
    target_field: str,
    reason: str = "low confidence",
) -> ReviewRecord:
    record = ReviewRecord(
        review_id=review_id,
        task_id=f"task_{review_id}",
        doc_id=f"doc_{review_id}",
        schema_id="procurement_doc",
        template_id="procurement_doc_base_v1",
        mapping_id=f"mapping_{review_id}",
        candidate_id=f"candidate_{review_id}",
        source_field_name=source_label,
        source_path="blocks[0].text",
        target_field_id=target_field,
        suggested_by="fuzzy",
        confidence=0.61,
        reason=reason,
        status="pending",
        decision="pending",
        reviewer="system",
    )
    session.add(record)
    session.commit()
    return record


def test_impact_preview_finds_related_future_mappings(tmp_path) -> None:
    session, service = make_service(tmp_path)
    add_review(
        session,
        review_id="r1",
        source_label="发文单位",
        target_field="issuer",
    )
    add_review(
        session,
        review_id="r2",
        source_label="发文单位",
        target_field="issuer",
    )

    preview = service.impact_preview("r1")

    assert preview.review_id == "r1"
    assert len(preview.would_affect) == 1
    assert preview.would_affect[0].doc_id == "doc_r2"
    assert preview.badcase_hits == []


def test_rejection_creates_negative_knowledge(tmp_path) -> None:
    session, service = make_service(tmp_path)
    review = add_review(
        session,
        review_id="r1",
        source_label="控制价",
        target_field="award_amount",
    )

    rule = service.record_negative_rule(review, reason="控制价不是中标金额")

    assert rule.source_label == "控制价"
    assert rule.forbidden_target == "award_amount"
    assert rule.source == "human_rejection"
    assert service.list_negative_rules() == [rule]


def test_batch_approve_rejects_high_risk_reviews(tmp_path) -> None:
    session, service = make_service(tmp_path)
    add_review(
        session,
        review_id="r1",
        source_label="控制价",
        target_field="award_amount",
        reason="risk_flags=control_price_not_award_amount",
    )
    add_review(
        session,
        review_id="r2",
        source_label="控制价",
        target_field="award_amount",
        reason="risk_flags=control_price_not_award_amount",
    )

    with pytest.raises(ValueError, match="high-risk"):
        service.batch_approve(
            ["r1", "r2"],
            reviewer="demo_user",
            comment="unsafe batch",
        )
