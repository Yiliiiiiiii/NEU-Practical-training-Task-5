from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import Settings
from app.schemas.topic5_convert import Topic5ConvertRequest
from app.schemas.topic5_execution import Topic5ExecutionOptions
from app.services.topic5_conversion_engine import (
    ConversionEngineContext,
    Topic5ConversionEngine,
)

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "eval"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: object) -> str:
    data = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_performance_fixtures_are_frozen_and_mixed_content() -> None:
    root = EVAL / "topic5_performance" / "v1"
    manifest = _json(root / "manifest.json")

    assert [item["block_count"] for item in manifest["fixtures"]] == [
        10,
        100,
        1000,
        10000,
    ]
    for item in manifest["fixtures"]:
        payload = _json(root / "fixtures" / item["path"])
        uir = payload["uir"]
        block_types = {block["type"] for block in uir["blocks"]}
        assert len(uir["blocks"]) == item["block_count"]
        assert {"paragraph", "heading", "list_item", "table"} <= block_types
        assert uir["metadata"]["fixture_block_count"] == item["block_count"]
        assert uir["entities"]
        assert any(block["attributes"].get("candidate_label") for block in uir["blocks"])
        assert _canonical_hash(payload) == item["sha256"]


def test_conversion_engine_exposes_required_performance_stages() -> None:
    payload = _json(
        EVAL / "topic5_performance" / "v1" / "fixtures" / "10.json"
    )
    request = Topic5ConvertRequest.model_validate(payload)
    options, warnings = Topic5ExecutionOptions.parse_legacy(request.options)

    result = Topic5ConversionEngine().convert(
        uir=request.uir,
        target_schema=request.target_schema,
        metadata_template=request.metadata_template,
        mapping_rules=request.effective_mapping_template,
        content_organization=request.content_organization,
        execution_options=options,
        output_assertions=None,
        engine_context=ConversionEngineContext(
            task_id="task11-timing",
            doc_id=request.uir.doc_id,
            input_mode="test",
            mapping_input_name=request.mapping_input_name,
            settings=Settings(),
            option_warnings=warnings,
        ),
    )

    assert {
        "candidate_extraction",
        "mapping",
        "transform",
        "render",
        "chunk",
        "validation",
        "verification",
        "total",
    } <= result.stage_durations_ms.keys()
    assert all(value >= 0 for value in result.stage_durations_ms.values())


def test_task11_evaluator_reports_satisfy_reliability_contract() -> None:
    performance = _json(EVAL / "topic5_performance" / "v1" / "baseline.json")
    concurrency = _json(EVAL / "topic5_concurrency" / "v1" / "report.json")
    faults = _json(EVAL / "topic5_package_faults" / "v1" / "report.json")
    downstream = _json(EVAL / "topic5_downstream" / "v1" / "report.json")

    assert performance["status"] == "passed"
    assert performance["case_count"] == 4
    assert performance["scaling"]["quadratic_blowup_detected"] is False
    assert performance["environment"]["logical_cpu_count"]
    assert concurrency["request_count"] >= 10
    assert concurrency["terminal_status_rate"] == 1.0
    assert concurrency["valid_package_rate"] == 1.0
    assert all(concurrency["checks"].values())
    assert faults["partial_package_survival_count"] == 0
    assert faults["temporary_cleanup_failure_count"] == 0
    assert faults["prior_package_preservation_rate"] == 1.0
    assert downstream["verified_package_export_pass_rate"] == 1.0
    assert downstream["invalid_package_rejection_rate"] == 1.0
    assert downstream["source_link_preservation_rate"] == 1.0
    assert downstream["invalid_package_export_acceptance"] == 0
