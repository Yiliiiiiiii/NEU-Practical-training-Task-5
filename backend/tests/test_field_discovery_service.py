from app.schemas.uir import UIRDocument
from app.services.field_discovery_service import FieldDiscoveryService


def make_sample(doc_id: str, rows: list[list[str]], paragraph: str) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": doc_id,
            "source": {"source_type": "external_uir", "source_name": "test"},
            "metadata": {"title": f"Sample {doc_id}"},
            "blocks": [
                {
                    "block_id": "b001",
                    "type": "table",
                    "attributes": {"rows": rows},
                },
                {
                    "block_id": "b002",
                    "type": "paragraph",
                    "text": paragraph,
                    "attributes": {},
                },
            ],
            "assets": [],
        }
    )


def samples() -> list[UIRDocument]:
    return [
        make_sample(
            f"sample_{index}",
            [
                ["项目名称" if index < 3 else "采购项目名称", f"Project {index}"],
                ["预算金额", f"{index + 1}00万元"],
            ],
            f"会议时间：2026年7月{index + 1}日",
        )
        for index in range(5)
    ]


def test_discovers_and_clusters_repeated_field_labels() -> None:
    result = FieldDiscoveryService().discover(samples())

    project_name = next(
        item for item in result.field_candidates if item.field_name == "project_name"
    )
    assert set(project_name.source_labels) == {"项目名称", "采购项目名称"}
    assert project_name.frequency == 1.0
    assert len(project_name.value_examples) == 5
    assert project_name.evidence_paths


def test_infers_date_type_from_colon_pattern_values() -> None:
    result = FieldDiscoveryService().discover(samples())

    meeting_date = next(
        item for item in result.field_candidates if item.field_name == "meeting_date"
    )
    assert meeting_date.inferred_type == "date"
    assert meeting_date.frequency == 1.0
    assert all("blocks[1].text" in path for path in meeting_date.evidence_paths)


def test_high_risk_amount_field_requires_review() -> None:
    result = FieldDiscoveryService().discover(samples())

    budget_amount = next(
        item for item in result.field_candidates if item.field_name == "budget_amount"
    )
    assert "budget_amount_not_award_amount" in budget_amount.risk_flags
    assert budget_amount.review_required is True
    assert budget_amount.inferred_type == "amount"
