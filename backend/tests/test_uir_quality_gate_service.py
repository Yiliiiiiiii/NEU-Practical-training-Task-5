from app.schemas.uir import UIRDocument
from app.services.uir_quality_gate_service import UIRQualityGateService


def make_uir(
    text: str,
    *,
    doc_id: str = "doc1",
    metadata: dict[str, str] | None = None,
    blocks: list[dict[str, object]] | None = None,
) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": doc_id,
            "source": {"source_type": "external_uir", "source_name": doc_id},
            "metadata": metadata
            if metadata is not None
            else {"title": text, "source_url": "https://example.test/doc"},
            "blocks": blocks
            if blocks is not None
            else [
                {
                    "block_id": "b001",
                    "type": "paragraph",
                    "text": text,
                    "attributes": {},
                }
            ],
            "assets": [],
        }
    )


def issue_codes(report: object) -> set[str]:
    return {issue.code for issue in report.issues}


def test_quality_gate_passes_supported_high_confidence_uir() -> None:
    report = UIRQualityGateService().evaluate(
        make_uir(
            "\u670d\u52a1\u6307\u5357 \u529e\u4e8b\u6307\u5357 \u7533\u8bf7\u6761\u4ef6 "
            "\u529e\u7406\u6d41\u7a0b \u6750\u6599\u6e05\u5355 \u670d\u52a1\u5bf9\u8c61 "
            "\u8054\u7cfb\u65b9\u5f0f"
        )
    )

    assert report.status == "pass"
    assert report.supported_doc_type == "general_doc"
    assert report.mapping_policy.allow_auto_accept is True


def test_quality_gate_rejects_empty_blocks() -> None:
    report = UIRQualityGateService().evaluate(make_uir("普通文本", blocks=[]))

    assert report.status == "reject"
    assert "missing_blocks" in issue_codes(report)
    assert report.mapping_policy.allow_llm_suggestions is False


def test_quality_gate_rejects_duplicate_block_ids() -> None:
    blocks = [
        {"block_id": "dup", "type": "paragraph", "text": "服务指南 办理流程", "attributes": {}},
        {"block_id": "dup", "type": "paragraph", "text": "材料清单 联系方式", "attributes": {}},
    ]

    report = UIRQualityGateService().evaluate(make_uir("服务指南", blocks=blocks))

    assert report.status == "reject"
    assert "duplicate_block_id" in issue_codes(report)


def test_quality_gate_marks_unsupported_low_confidence_text() -> None:
    report = UIRQualityGateService().evaluate(make_uir("普通说明文本，没有明确业务关键词"))

    assert report.status == "unsupported"
    assert "unsupported_schema_family" in issue_codes(report)


def test_quality_gate_uses_metadata_doc_type_as_review_only_fallback() -> None:
    report = UIRQualityGateService().evaluate(
        make_uir(
            "普通说明文本，没有明确业务关键词",
            metadata={
                "title": "普通说明",
                "doc_type": "general_doc",
                "source_url": "https://example.test/doc",
            },
        )
    )

    assert report.status == "review"
    assert report.supported_doc_type == "general_doc"
    assert "metadata_schema_fallback" in issue_codes(report)
    assert report.mapping_policy.allow_auto_accept is False


def test_quality_gate_requires_review_without_source_evidence() -> None:
    report = UIRQualityGateService().evaluate(
        make_uir(
            "服务指南 办事指南 申请条件 办理流程 材料清单 服务对象 联系方式",
            metadata={"title": "服务指南"},
        )
    )

    assert report.status == "review"
    assert "missing_source_evidence" in issue_codes(report)
    assert report.mapping_policy.allow_auto_accept is False


def test_quality_gate_requires_review_for_mojibake_text() -> None:
    report = UIRQualityGateService().evaluate(
        make_uir(
            "鏈嶅姟鎸囧崡 鍔炰簨鎸囧崡 鐢宠鏉′欢 鍔炵悊娴佺▼ "
            "鏉愭枡娓呭崟 鏈嶅姟瀵硅薄 鑱旂郴鏂瑰紡"
        )
    )

    assert report.status in {"review", "unsupported"}
    assert "possible_mojibake" in issue_codes(report)
