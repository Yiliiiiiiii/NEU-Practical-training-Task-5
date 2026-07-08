import json
from pathlib import Path

from scripts import check_production_shadow_gold_coverage


def test_missing_production_shadow_writes_blocker_report(tmp_path: Path) -> None:
    out = tmp_path / "coverage.json"
    markdown = tmp_path / "coverage.md"

    exit_code = check_production_shadow_gold_coverage.main(
        [
            "--manifest",
            str(tmp_path / "missing_manifest.json"),
            "--gold",
            str(tmp_path / "missing_gold.jsonl"),
            "--out",
            str(out),
            "--markdown",
            str(markdown),
            "--blocker-markdown",
            str(tmp_path / "blocker.md"),
        ]
    )

    assert exit_code == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert report["can_claim_0_85"] is False
    assert "independent production blind UIR corpus" in report["reason"]
    assert "Cannot claim 0.85" in markdown.read_text(encoding="utf-8")


def test_gold_coverage_checks_blind_docs_have_required_gold(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    gold = tmp_path / "mapping_gold.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "dataset_id": "production_shadow_v1",
                "documents": [
                    {
                        "doc_id": "blind_policy_001",
                        "path": "blind/policy/doc.json",
                        "split": "blind",
                        "doc_type": "policy_doc",
                        "schema_id": "policy_doc",
                        "template_id": "policy_doc_base_v1",
                        "quality_gate_expected": "pass",
                        "gold_path": "gold/mapping_gold.jsonl",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    gold.write_text(
        json.dumps(
            {
                "doc_id": "blind_policy_001",
                "doc_type": "policy_doc",
                "schema_id": "policy_doc",
                "target_field": "publish_date",
                "expected_value": "2026-02-06",
                "source_block_ids": ["b1"],
                "source_quote": "publish date: 2026-02-06",
                "required": True,
                "accept_review_required": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "coverage.json"
    markdown = tmp_path / "coverage.md"

    exit_code = check_production_shadow_gold_coverage.main(
        [
            "--manifest",
            str(manifest),
            "--gold",
            str(gold),
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["blind_doc_count"] == 1
    assert report["gold_label_count"] == 1


def test_empty_production_shadow_scaffold_stays_blocked(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    gold = tmp_path / "mapping_gold.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "dataset_id": "production_shadow_v1",
                "split": "blind",
                "frozen_at": None,
                "docs": [],
                "dedupe_against": ["examples/real_world"],
                "gold_policy": {"allows_runtime_use": False},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    gold.write_text("", encoding="utf-8")
    out = tmp_path / "coverage.json"
    markdown = tmp_path / "coverage.md"

    exit_code = check_production_shadow_gold_coverage.main(
        [
            "--manifest",
            str(manifest),
            "--gold",
            str(gold),
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert report["can_claim_0_85"] is False
