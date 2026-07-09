from __future__ import annotations

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def test_candidate_service_generic_mode_ignores_domain_specific_derivations():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "meeting_generic",
            "metadata": {"domain": "meeting_doc", "标题": "泛化候选测试"},
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "2026年7月9日下午，区长主持召开项目会议。",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )

    generic = CandidateService().extract_candidates(
        "task_generic",
        uir,
        enable_legacy_domain_rules=False,
    )
    legacy = CandidateService().extract_candidates(
        "task_legacy",
        uir,
        enable_legacy_domain_rules=True,
    )

    assert all(candidate.source_name != "meeting date" for candidate in generic)
    assert any(candidate.source_name == "meeting date" for candidate in legacy)
    assert any(candidate.source_name == "标题" for candidate in generic)
    assert any(candidate.source_name == "document text" for candidate in generic)


def test_candidate_service_generic_mode_uses_candidate_profile_hints():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "announcement_generic",
            "metadata": {},
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "发布单位：信息化办公室",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )

    candidates = CandidateService().extract_candidates(
        "task_profile",
        uir,
        candidate_profile={"labeled_values": {"issuer": ["发布单位"]}},
        enable_legacy_domain_rules=False,
    )

    issuer = next(candidate for candidate in candidates if candidate.source_name == "issuer")
    assert issuer.value_sample == "信息化办公室"
    assert issuer.source_blocks == ["b1"]
    assert any("candidate_profile" in item for item in issuer.evidence)
