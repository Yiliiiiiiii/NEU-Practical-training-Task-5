from __future__ import annotations

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def _candidate_by_path(candidates, source_path: str):
    return next(candidate for candidate in candidates if candidate.source_path == source_path)


def test_candidate_service_generic_mode_ignores_domain_specific_derivations():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "meeting_generic",
            "metadata": {"domain": "meeting_doc", "title": "Meeting notice"},
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "会议于2026-07-09召开。",
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
    assert any(candidate.source_name == "title" for candidate in generic)
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
                    "text": "issuer: Information Office",
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
        candidate_profile={"labeled_values": {"issuer": ["issuer"]}},
        enable_legacy_domain_rules=False,
    )

    issuer = next(candidate for candidate in candidates if candidate.source_name == "issuer")
    assert issuer.value_sample == "Information Office"
    assert issuer.source_blocks == ["b1"]
    assert issuer.evidence_type == "candidate_profile"
    assert "issuer" in issuer.target_hints


def test_candidate_service_generic_mode_ignores_policy_metadata_enrichment():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_generic_metadata",
            "metadata": {
                "domain": "policy_doc",
                "issuer": "Some Office",
                "publishDate": "2026-07-09",
            },
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )

    candidates = CandidateService().extract_candidates(
        "task_generic",
        uir,
        enable_legacy_domain_rules=False,
    )

    issuer = _candidate_by_path(candidates, "$.metadata.issuer")
    assert issuer.display_name == "issuer"
    assert issuer.target_hints == []
    assert issuer.evidence_type == "metadata"


def test_candidate_service_legacy_mode_preserves_policy_metadata_enrichment():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_legacy_metadata",
            "metadata": {
                "domain": "policy_doc",
                "issuer": "Some Office",
                "publishDate": "2026-07-09",
            },
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )

    candidates = CandidateService().extract_candidates(
        "task_legacy",
        uir,
        enable_legacy_domain_rules=True,
    )

    issuer = _candidate_by_path(candidates, "$.metadata.issuer")
    assert issuer.display_name == "issuer"
    assert "issuer" in issuer.target_hints
