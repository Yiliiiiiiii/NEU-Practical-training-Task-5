import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_package(root: Path, *, blocked: bool = False) -> None:
    package = root / "pkg_one"
    package.mkdir(parents=True)
    write_json(
        package / "manifest.json",
        {
            "doc_id": "doc_review_001",
            "generator": {"schema_id": "meeting_doc"},
        },
    )
    write_json(
        package / "canonical.json",
        {
            "blocks": [
                {
                    "block_id": "b1",
                    "text": "出席：张三、李四；主持人：王五。",
                }
            ]
        },
    )
    write_json(
        package / "mapping_report.json",
        {
            "schema_id": "meeting_doc",
            "review_required_items": [
                {
                    "candidate_id": "cand_attendees",
                    "target_field_id": "attendees",
                    "source_field_name": "出席",
                    "source_field": {
                        "source_name": "出席",
                        "source_path": "$.blocks.b1.text#attendees",
                    },
                    "value_sample": "张三、李四",
                    "source_blocks": ["b1"],
                    "confidence": 0.62,
                    "confidence_tier": "low",
                    "risk_flags": ["medium_risk_mixed_attendee_roles"],
                    "badcase_filter": {"blocked": blocked},
                    "review_required_reason": "Mapping evidence has semantic risk.",
                }
            ],
        },
    )


def test_build_review_evidence_pack_includes_source_excerpt(tmp_path: Path) -> None:
    make_package(tmp_path)
    module = load_script("build_review_evidence_pack")

    pack = module.build_pack(tmp_path)

    assert pack["summary"]["review_count"] == 1
    item = pack["reviews"][0]
    assert item["requires_human"] is True
    assert item["codex_suggestion"] == "keep_pending"
    assert item["source_excerpt"] == "出席：张三、李四；主持人：王五。"
    assert item["lineage_available"] is True


def test_build_review_evidence_pack_suggests_reject_for_blocked_badcase(
    tmp_path: Path,
) -> None:
    make_package(tmp_path, blocked=True)
    module = load_script("build_review_evidence_pack")

    pack = module.build_pack(tmp_path)

    assert pack["reviews"][0]["codex_suggestion"] == "reject"
    assert pack["summary"]["suggest_reject"] == 1


def test_apply_manual_decisions_skips_when_no_manual_decision() -> None:
    module = load_script("apply_manual_review_decisions")
    report = module.apply_decisions(
        {"reviews": [{"review_id": "rev_one", "target_field": "issuer"}]},
        {},
    )

    assert report["summary"]["applied_count"] == 0
    assert report["skipped"][0]["reason"] == "no_manual_decision"
    assert report["summary"]["external_mutations"] == 0


def test_apply_manual_decisions_requires_human_for_approve() -> None:
    module = load_script("apply_manual_review_decisions")
    evidence = {
        "reviews": [
            {
                "review_id": "rev_one",
                "doc_id": "doc",
                "target_field": "issuer",
                "risk_flags": ["medium_risk_issuer"],
                "codex_suggestion": "keep_pending",
            }
        ]
    }

    skipped = module.apply_decisions(
        evidence,
        {"rev_one": {"review_id": "rev_one", "decision": "approve", "operator": "codex"}},
    )
    applied = module.apply_decisions(
        evidence,
        {"rev_one": {"review_id": "rev_one", "decision": "approve", "operator": "human"}},
    )

    assert skipped["summary"]["applied_count"] == 0
    assert skipped["skipped"][0]["reason"] == "approve_requires_human_operator"
    assert applied["summary"]["applied_approve"] == 1
    assert applied["applied"][0]["warnings"] == [
        "approved_review_has_risk_flags",
        "manual_approve_overrides_non_approve_suggestion",
    ]
