import json

from app.services.evaluation_center_service import EvaluationCenterService
from app.services.storage_service import StorageService


def test_registers_runs_and_builds_passing_scorecard(tmp_path) -> None:
    service = EvaluationCenterService(
        StorageService(tmp_path / "storage"),
        dataset_registry_path=tmp_path / "datasets.json",
        reports_root=tmp_path / "reports",
    )
    (tmp_path / "datasets.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "dataset_id": "real_world_uir",
                        "dataset_type": "real_world_uir",
                        "doc_count": 45,
                        "doc_types": {"general_doc": 10},
                        "gold_files": ["mapping_gold.jsonl"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run = service.register_run(
        dataset_id="real_world_uir",
        eval_type="adapter_framework",
        metrics={
            "adapter_trace_coverage": 1.0,
            "badcase_violation_count": 0,
            "llm_auto_accepted_count": 0,
            "package_verification_rate": 1.0,
            "lineage_parse_pass_rate": 1.0,
            "lineage_broken_edges": 0,
            "lineage_secret_leaks": 0,
            "lineage_field_coverage": 1.0,
        },
        report_paths={"json": "reports/adapter.json"},
        git_commit="abc123",
    )

    assert run.passed is True
    assert service.list_runs()[0].run_id == run.run_id
    scorecard = service.scorecard()
    assert scorecard.passed is True
    assert scorecard.run_count == 1
    assert scorecard.failed_gates == []
    assert scorecard.summary.status == "passed"
    assert scorecard.summary.gates_passed == 8
    assert scorecard.summary.gates_total == 8
    cards = {card.metric_id: card for card in scorecard.cards}
    assert cards["package_verification_rate"].status == "passed"
    assert cards["strict_validation_rate"].status == "needs_attention"
    assert cards["lineage_parse_pass_rate"].status == "passed"
    assert cards["lineage_field_coverage"].status == "passed"
    assert any(
        "does not imply" in warning.lower()
        for warning in scorecard.warnings
    )


def test_scorecard_exposes_failed_hard_gates(tmp_path) -> None:
    registry = tmp_path / "datasets.json"
    registry.write_text('{"items":[]}', encoding="utf-8")
    service = EvaluationCenterService(
        StorageService(tmp_path / "storage"),
        dataset_registry_path=registry,
        reports_root=tmp_path / "reports",
    )

    run = service.register_run(
        dataset_id="adhoc",
        eval_type="unsafe",
        metrics={
            "adapter_trace_coverage": 0.5,
            "badcase_violation_count": 1,
            "llm_auto_accepted_count": 1,
            "package_verification_rate": 0.8,
        },
        report_paths={},
        git_commit="dirty",
    )

    assert run.passed is False
    assert {item.metric for item in run.failed_gates} == {
        "adapter_trace_coverage",
        "badcase_violation_count",
        "llm_auto_accepted_count",
        "package_verification_rate",
    }
    scorecard = service.scorecard()
    cards = {card.metric_id: card for card in scorecard.cards}
    assert scorecard.summary.status == "failed"
    assert cards["badcase_violation_count"].status == "failed"
    assert cards["llm_auto_accepted_count"].status == "failed"


def test_scorecard_exposes_failed_lineage_gates(tmp_path) -> None:
    registry = tmp_path / "datasets.json"
    registry.write_text('{"items":[]}', encoding="utf-8")
    service = EvaluationCenterService(
        StorageService(tmp_path / "storage"),
        dataset_registry_path=registry,
        reports_root=tmp_path / "reports",
    )

    run = service.register_run(
        dataset_id="lineage",
        eval_type="lineage",
        metrics={
            "lineage_parse_pass_rate": 0.5,
            "lineage_broken_edges": 1,
            "lineage_secret_leaks": 1,
            "lineage_field_coverage": 0.5,
        },
        report_paths={"json": "reports/lineage_eval_report.json"},
        git_commit="dirty",
    )

    assert run.passed is False
    assert {item.metric for item in run.failed_gates} == {
        "lineage_parse_pass_rate",
        "lineage_broken_edges",
        "lineage_secret_leaks",
        "lineage_field_coverage",
    }
    cards = {card.metric_id: card for card in service.scorecard().cards}
    assert cards["lineage_parse_pass_rate"].status == "failed"
    assert cards["lineage_field_coverage"].status == "failed"
