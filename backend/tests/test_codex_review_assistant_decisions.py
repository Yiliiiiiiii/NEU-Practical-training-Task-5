from scripts.codex_review_assistant import decide_review


def review(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "review_id": "review_1",
        "task_id": "task_1",
        "doc_id": "doc_1",
        "doc_type": "general_doc",
        "schema_id": "general_doc",
        "template_id": "general_doc_base_v1",
        "source_label": "服务对象",
        "source_value": "本市中小企业",
        "target_field": "service_object",
        "confidence": 0.9,
        "confidence_tier": "high",
        "evidence": [{"type": "section_heading", "message": "明确章节"}],
        "source_path": "$.blocks.b1.text",
        "source_blocks": ["b1"],
        "risk_flags": [],
        "badcase_filter": {"blocked": False},
        "suggested_by": "exact",
    }
    item.update(overrides)
    return item


def test_high_confidence_safe_review_is_approved() -> None:
    decision = decide_review(review())

    assert decision["decision_suggestion"] == "approve"
    assert decision["safe_to_apply"] is True


def test_forbidden_pair_is_rejected() -> None:
    decision = decide_review(
        review(
            source_label="成文日期",
            target_field="publish_date",
            source_value="2025年6月1日",
        )
    )

    assert decision["decision_suggestion"] == "reject"
    assert decision["safe_to_apply"] is True
    assert "forbidden" in decision["reason"]


def test_medium_confidence_stays_pending() -> None:
    decision = decide_review(
        review(confidence=0.7, confidence_tier="medium")
    )

    assert decision["decision_suggestion"] == "keep_pending"
    assert decision["safe_to_apply"] is False


def test_llm_only_suggestion_stays_pending() -> None:
    decision = decide_review(review(suggested_by="llm_fallback"))

    assert decision["decision_suggestion"] == "keep_pending"
    assert "LLM" in decision["reason"]


def test_missing_source_path_stays_pending() -> None:
    decision = decide_review(review(source_path=None))

    assert decision["decision_suggestion"] == "keep_pending"
    assert "trace" in decision["reason"].lower()


def test_high_risk_target_with_weak_evidence_stays_pending() -> None:
    decision = decide_review(
        review(
            doc_type="policy_doc",
            source_label="发布机构",
            target_field="issuer",
            evidence=[{"type": "page_publisher_field"}],
            risk_flags=["medium_risk_issuer"],
        )
    )

    assert decision["decision_suggestion"] == "keep_pending"
    assert decision["safe_to_apply"] is False

