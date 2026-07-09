import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
REAL_WORLD_DIR = ROOT / "examples" / "real_world"
UIR_DIR = REAL_WORLD_DIR / "uir"
MAPPING_GOLD_PATH = REAL_WORLD_DIR / "gold" / "mapping_gold.jsonl"
BADCASES_PATH = REAL_WORLD_DIR / "gold" / "real_world_badcases.jsonl"
SCHEMA_DIR = ROOT / "examples" / "production_like" / "schemas"

EXPECTED_DOC_TYPES = {
    "policy_doc",
    "procurement_doc",
    "meeting_doc",
    "general_doc",
}
EXPECTED_BADCASE_TYPES = {
    "ambiguous_date",
    "multiple_amounts",
    "similar_org_roles",
    "irregular_heading",
    "flattened_complex_table",
    "general_schema_overload",
    "semantic_role_confusion",
}
PROCUREMENT_TARGET_FIELDS = {
    "title",
    "project_name",
    "procurement_id",
    "procurement_type",
    "purchaser",
    "agency",
    "budget_amount",
    "award_supplier",
    "award_amount",
    "announcement_date",
    "bid_deadline",
    "opening_date",
    "contact_person",
    "contact_phone",
    "source_url",
    "source_site",
    "summary",
    "content",
}
VALID_BADCASE_SEVERITIES = {"low", "medium", "high", "critical"}
SOURCE_PATH_SEGMENT = re.compile(r"^(?P<name>[^\[\]]+)(?:\[(?P<index>\*|\d+)\])?$")


def load_script(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AssertionError(
                    f"{path}:{line_number} is not valid JSON: {exc.msg}"
                ) from exc
            assert isinstance(row, dict), f"{path}:{line_number} must contain an object"
            rows.append(row)
    return rows


def source_path_exists(document: dict[str, Any], source_path: str) -> bool:
    nodes: list[Any] = [document]
    for segment in source_path.split("."):
        match = SOURCE_PATH_SEGMENT.fullmatch(segment)
        if match is None:
            return False
        name = match.group("name")
        index = match.group("index")
        next_nodes: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict) or name not in node:
                return False
            value = node[name]
            if index is None:
                next_nodes.append(value)
                continue
            if not isinstance(value, list) or not value:
                return False
            if index == "*":
                next_nodes.extend(value)
                continue
            position = int(index)
            if position >= len(value):
                return False
            next_nodes.append(value[position])
        nodes = next_nodes
    return bool(nodes)


def source_path_values(document: dict[str, Any], source_path: str) -> list[Any]:
    nodes: list[Any] = [document]
    for segment in source_path.split("."):
        match = SOURCE_PATH_SEGMENT.fullmatch(segment)
        assert match is not None, f"invalid source_path syntax: {source_path}"
        name = match.group("name")
        index = match.group("index")
        next_nodes: list[Any] = []
        for node in nodes:
            assert isinstance(node, dict) and name in node, (
                f"source_path does not exist: {source_path}"
            )
            value = node[name]
            if index is None:
                next_nodes.append(value)
            elif index == "*":
                assert isinstance(value, list)
                next_nodes.extend(value)
            else:
                assert isinstance(value, list)
                next_nodes.append(value[int(index)])
        nodes = next_nodes
    return nodes


def assert_nonempty_string(value: Any, message: str) -> None:
    assert isinstance(value, str) and value.strip(), message


def validate_mapping_row(
    row: dict[str, Any],
    uir: dict[str, Any],
    allowed_target_fields: set[str],
) -> None:
    doc_id = row["doc_id"]
    expected_mappings = row.get("expected_mappings")
    assert isinstance(expected_mappings, list), (
        f"{doc_id}: expected_mappings must be a list"
    )
    assert len(expected_mappings) >= 3, (
        f"{doc_id}: expected_mappings must contain at least 3 entries"
    )
    target_fields: list[str] = []
    for mapping in expected_mappings:
        assert isinstance(mapping, dict), f"{doc_id}: mapping must be an object"
        target_field = mapping.get("target_field")
        assert_nonempty_string(target_field, f"{doc_id}: mapping target is required")
        assert target_field in allowed_target_fields, (
            f"{doc_id}: invalid mapping target {target_field}"
        )
        source_path = mapping.get("source_path")
        assert_nonempty_string(source_path, f"{doc_id}: mapping source_path is required")
        assert source_path_exists(uir, source_path), (
            f"{doc_id}: mapping source_path does not exist: {source_path}"
        )
        target_fields.append(target_field)
    assert len(set(target_fields)) == len(target_fields), (
        f"{doc_id}: expected mappings must use distinct target fields"
    )

    expected_reviews = row.get("expected_review_required")
    assert isinstance(expected_reviews, list), (
        f"{doc_id}: expected_review_required must be a list"
    )
    assert expected_reviews, f"{doc_id}: expected_review_required must not be empty"
    for review in expected_reviews:
        assert isinstance(review, dict), f"{doc_id}: review must be an object"
        assert_nonempty_string(review.get("reason"), f"{doc_id}: review reason is required")
        target_field = review.get("target_field")
        assert_nonempty_string(target_field, f"{doc_id}: review target is required")
        assert target_field in allowed_target_fields, (
            f"{doc_id}: invalid review target {target_field}"
        )
        source_path = review.get("source_path")
        assert_nonempty_string(source_path, f"{doc_id}: review source_path is required")
        assert source_path_exists(uir, source_path), (
            f"{doc_id}: review source_path does not exist: {source_path}"
        )

    known_badcases = row.get("known_badcases")
    assert isinstance(known_badcases, list), f"{doc_id}: known_badcases must be a list"
    for badcase in known_badcases:
        assert isinstance(badcase, dict), f"{doc_id}: badcase must be an object"
        assert_nonempty_string(badcase.get("case_id"), f"{doc_id}: badcase case_id required")
        assert badcase.get("doc_id") == doc_id, f"{doc_id}: badcase doc_id must match"
        badcase_type = badcase.get("badcase_type")
        assert badcase_type in EXPECTED_BADCASE_TYPES, (
            f"{doc_id}: invalid badcase type {badcase_type}"
        )
        assert_nonempty_string(
            badcase.get("expected_behavior"),
            f"{doc_id}: badcase expected_behavior is required",
        )
        assert badcase.get("severity") in VALID_BADCASE_SEVERITIES, (
            f"{doc_id}: invalid badcase severity"
        )

        forbidden = badcase.get("forbidden_auto_mapping")
        assert isinstance(forbidden, dict), f"{doc_id}: forbidden mapping is required"
        assert_nonempty_string(
            forbidden.get("source_name"),
            f"{doc_id}: forbidden source is required",
        )
        forbidden_target = forbidden.get("target_field")
        assert_nonempty_string(
            forbidden_target,
            f"{doc_id}: forbidden target is required",
        )
        assert forbidden_target in allowed_target_fields, (
            f"{doc_id}: invalid badcase target {forbidden_target}"
        )

        evidence = badcase.get("source_evidence")
        assert isinstance(evidence, dict), f"{doc_id}: source evidence is required"
        source_paths = evidence.get("source_paths")
        assert isinstance(source_paths, list) and source_paths, (
            f"{doc_id}: source evidence paths are required"
        )
        assert_nonempty_string(
            evidence.get("excerpt"),
            f"{doc_id}: source evidence excerpt is required",
        )
        for source_path in source_paths:
            assert_nonempty_string(
                source_path,
                f"{doc_id}: source evidence path is required",
            )
            assert source_path_exists(uir, source_path), (
                f"{doc_id}: source evidence path does not exist: {source_path}"
            )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(f"{json.dumps(row, ensure_ascii=False)}\n" for row in rows),
        encoding="utf-8",
    )


def run_contract_with_temp_data(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mapping_rows: list[dict[str, Any]],
    badcases: list[dict[str, Any]],
) -> None:
    mapping_path = tmp_path / "mapping_gold.jsonl"
    badcases_path = tmp_path / "real_world_badcases.jsonl"
    write_jsonl(mapping_path, mapping_rows)
    write_jsonl(badcases_path, badcases)
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "MAPPING_GOLD_PATH", mapping_path)
    monkeypatch.setattr(module, "BADCASES_PATH", badcases_path)
    test_real_world_mapping_gold_is_valid_jsonl()


def assert_row_source_path_matches_uir(
    row: dict[str, Any],
    expected_uir: dict[str, Any],
) -> None:
    doc_id = row["doc_id"]
    source_path = row.get("source_path")
    assert_nonempty_string(source_path, f"{doc_id}: row source_path is required")
    resolved_path = ROOT / source_path
    assert resolved_path.is_file(), (
        f"{doc_id}: row source_path does not exist: {source_path}"
    )
    source_uir = json.loads(resolved_path.read_text(encoding="utf-8"))
    assert source_uir.get("doc_id") == doc_id, (
        f"{doc_id}: row source_path doc_id must match"
    )
    assert source_uir == expected_uir, (
        f"{doc_id}: row source_path must point to the matching UIR document"
    )


def test_mapping_metrics_count_accepted_review_missing_and_badcases() -> None:
    eval_support = load_script("eval_support")
    gold = {
        "doc_id": "real_procurement_001",
        "expected_mappings": [
            {
                "source_name": "项目名称",
                "source_path": "blocks[0].text",
                "target_field": "project_name",
                "required": True,
            },
            {
                "source_name": "采购人",
                "source_path": "blocks[1].text",
                "target_field": "purchaser",
                "required": True,
            },
        ],
        "expected_review_required": [
            {
                "source_name": "预算金额",
                "source_path": "blocks[2].text",
                "target_field_candidates": ["budget_amount", "award_amount"],
                "reason": "budget and award amounts are ambiguous",
            }
        ],
        "known_badcases": [
            {
                "case_id": "badcase-budget-not-award",
                "forbidden_auto_mapping": {
                    "source_name": "预算金额",
                    "target_field": "award_amount",
                },
            },
            {
                "case_id": "badcase-purchaser-not-agency",
                "source_name": "采购人",
                "forbidden_target_field": "agency",
            },
        ],
    }
    report = {
        "mappings": [
            {
                "source_field": {
                    "source_name": "项目名称",
                    "source_path": "blocks[0].text",
                },
                "target_field_id": "project_name",
                "status": "accepted",
            }
        ],
        "review_required_items": [
            {
                "source_name": "预算金额",
                "source_path": "blocks[2].text",
                "target_field_candidates": ["budget_amount", "award_amount"],
            }
        ],
        "unmapped_required_fields": ["purchaser"],
    }

    metrics = eval_support.score_mapping_report(gold, report)

    assert metrics["auto_accepted_correct"] == 1
    assert metrics["review_required_correct"] == 1
    assert metrics["missing_gold_mappings"] == 1
    assert metrics["badcase_violation_count"] == 0
    assert metrics["mapping_recall"] == pytest.approx(2 / 3)
    assert metrics["auto_mapping_recall"] == pytest.approx(1 / 3)
    assert metrics["assisted_mapping_recall"] == pytest.approx(2 / 3)
    assert metrics["review_required_recall"] == pytest.approx(1 / 3)
    assert metrics["review_required_rate"] == pytest.approx(0.5)


def test_mapping_metrics_count_badcase_violation_for_forbidden_acceptance() -> None:
    eval_support = load_script("eval_support")
    gold = {
        "doc_id": "real_procurement_001",
        "expected_mappings": [],
        "expected_review_required": [],
        "known_badcases": [
            {
                "case_id": "badcase-budget-not-award",
                "forbidden_auto_mapping": {
                    "source_name": "预算金额",
                    "target_field": "award_amount",
                },
            }
        ],
    }
    report = {
        "mappings": [
            {
                "source_name": "预算金额",
                "target_field": "award_amount",
                "status": "accepted",
            }
        ],
        "review_required_items": [],
    }

    metrics = eval_support.score_mapping_report(gold, report)

    assert metrics["badcase_violation_count"] == 1


def test_mapping_eval_generates_required_json_and_markdown_sections() -> None:
    evaluator = load_script("eval_real_world_mapping")

    report = evaluator.build_report(
        [
            {
                "doc_id": "doc_1",
                "doc_type": "policy_doc",
                "metrics": {
                    "gold_mapping_count": 2,
                    "gold_review_required_count": 1,
                    "auto_accepted_correct": 2,
                    "review_required_correct": 1,
                    "missing_gold_mappings": 0,
                    "badcase_violation_count": 0,
                    "badcase_violations": [],
                    "mapping_recall": 1.0,
                },
                "package_passed": True,
                "review_evidence": [{"target_field": "publish_date"}],
            }
        ]
    )
    markdown = evaluator.render_markdown(report)

    assert report["summary"]["document_count"] == 1
    assert report["summary"]["package_pass_rate"] == 1.0
    assert report["summary"]["badcase_violation_count"] == 0
    assert report["summary"]["auto_mapping_recall"] == pytest.approx(2 / 3)
    assert report["summary"]["assisted_mapping_recall"] == 1.0
    assert "## Per Document Type" in markdown
    assert "Auto mapping recall" in markdown
    assert "Assisted mapping recall" in markdown
    assert "## Badcase Violations" in markdown
    assert "## Package Verification Summary" in markdown


def test_mapping_eval_resolves_gold_source_path_against_custom_uir_dir(
    tmp_path: Path,
) -> None:
    evaluator = load_script("eval_real_world_mapping")
    gold = {
        "source_path": (
            "examples/real_world/uir/procurement/"
            "real_procurement_001_broadcast_security_supervision.json"
        )
    }

    assert evaluator.resolve_uir_path(gold, tmp_path) == (
        tmp_path / "procurement" / "real_procurement_001_broadcast_security_supervision.json"
    )


def test_mapping_eval_treats_malformed_base_url_as_fatal() -> None:
    import httpx

    evaluator = load_script("eval_real_world_mapping")

    assert evaluator._is_fatal_http_error(
        httpx.UnsupportedProtocol("missing scheme")
    )


def test_split_evaluator_builds_generalization_summary() -> None:
    split_eval = load_script("eval_mapping_splits")
    source_report = {
        "documents": [
            {
                "doc_id": "dev_doc",
                "doc_type": "policy_doc",
                "metrics": {
                    "gold_signal_count": 2,
                    "gold_mapping_count": 2,
                    "auto_accepted_correct": 1,
                    "review_required_correct": 1,
                    "accepted_item_count": 1,
                    "review_required_item_count": 1,
                    "missing_gold_mappings": 0,
                    "badcase_violation_count": 0,
                    "badcase_violations": [],
                },
                "package_passed": True,
                "validation_passed": True,
                "review_evidence": [],
            },
            {
                "doc_id": "test_doc",
                "doc_type": "policy_doc",
                "metrics": {
                    "gold_signal_count": 2,
                    "gold_mapping_count": 2,
                    "auto_accepted_correct": 1,
                    "review_required_correct": 1,
                    "accepted_item_count": 1,
                    "review_required_item_count": 1,
                    "missing_gold_mappings": 0,
                    "badcase_violation_count": 0,
                    "badcase_violations": [],
                },
                "package_passed": True,
                "validation_passed": True,
                "review_evidence": [],
            },
            {
                "doc_id": "blind_doc",
                "doc_type": "policy_doc",
                "metrics": {
                    "gold_signal_count": 2,
                    "gold_mapping_count": 2,
                    "auto_accepted_correct": 1,
                    "review_required_correct": 1,
                    "accepted_item_count": 1,
                    "review_required_item_count": 1,
                    "missing_gold_mappings": 0,
                    "badcase_violation_count": 0,
                    "badcase_violations": [],
                },
                "package_passed": True,
                "validation_passed": True,
                "review_evidence": [],
            },
        ]
    }
    manifest = {
        "version": "test",
        "dev": {"doc_ids": ["dev_doc"]},
        "test": {"doc_ids": ["test_doc"]},
        "blind": {"doc_ids": ["blind_doc"]},
    }

    summary = split_eval.build_split_reports(
        manifest=manifest,
        source_report=source_report,
    )

    assert [row["split"] for row in summary["splits"]] == ["dev", "test", "blind"]
    assert summary["generalization_gap"]["conclusion"] == "pass"


def test_quality_gate_reports_threshold_failures() -> None:
    gate = load_script("check_mapping_quality_gate")
    result = gate.check_report(
        {
            "splits": [
                {
                    "split": "dev",
                    "assisted_mapping_recall": 0.7,
                    "badcase_violations": 1,
                    "required_missing": 2,
                }
            ],
            "generalization_gap": {
                "dev_vs_test_assisted_recall": 0.2,
                "test_vs_blind_assisted_recall": 0.0,
            },
        },
        min_assisted_recall=0.85,
        max_badcase_violations=0,
        max_required_missing=0,
        max_dev_test_gap=0.05,
        max_test_blind_gap=0.05,
    )

    assert not result["passed"]
    assert result["failure_count"] == 4


def test_handoff_docs_reference_all_four_reports() -> None:
    required = {
        "reports/real_world_mapping_eval_report.md",
        "reports/procurement_doc_eval_report.md",
        "reports/content_organization_retrieval_eval.md",
        "reports/knowledge_loop_eval_report.md",
    }
    text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/real_world_uir_dataset.md",
            "docs/交接/requirement_mapping.md",
            "docs/交接/final_demo_script.md",
            "docs/交接/final_handoff_status.md",
        )
    )

    assert required <= {item for item in required if item in text}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda row: row["expected_mappings"][1].update(
                target_field=row["expected_mappings"][0]["target_field"]
            ),
            "distinct target",
        ),
        (
            lambda row: row["expected_mappings"].clear(),
            "expected_mappings",
        ),
        (
            lambda row: row["expected_mappings"][0].pop("source_path"),
            "source_path",
        ),
        (
            lambda row: row["expected_mappings"][0].update(
                source_path="metadata.fabricated"
            ),
            "source_path",
        ),
        (
            lambda row: row["expected_review_required"][0].pop("target_field"),
            "review.*target",
        ),
        (
            lambda row: row.update(expected_review_required=[]),
            "expected_review_required",
        ),
        (
            lambda row: row["expected_review_required"][0].update(
                source_path="blocks[999].text"
            ),
            "review source_path",
        ),
        (
            lambda row: row["known_badcases"][0].update(doc_id="wrong-doc"),
            "badcase doc_id",
        ),
        (
            lambda row: row["known_badcases"][0]["forbidden_auto_mapping"].update(
                target_field="not_a_schema_field"
            ),
            "badcase target",
        ),
        (
            lambda row: row["known_badcases"][0]["source_evidence"].update(
                source_paths=["blocks[999].text"]
            ),
            "source evidence",
        ),
        (
            lambda row: row["known_badcases"][0]["source_evidence"].pop(
                "source_paths"
            ),
            "source evidence paths",
        ),
        (
            lambda row: row["known_badcases"][0].pop("expected_behavior"),
            "expected_behavior",
        ),
        (
            lambda row: row.pop("source_path"),
            "row source_path",
        ),
        (
            lambda row: row.update(
                source_path="examples/real_world/uir/general/missing.json"
            ),
            "row source_path",
        ),
        (
            lambda row: row.update(
                source_path=(
                    "examples/real_world/uir/general/"
                    "real_general_002_biomed_project_guide.json"
                )
            ),
            "row source_path doc_id",
        ),
    ],
)
def test_contract_rejects_malformed_mapping_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutate: Any,
    message: str,
) -> None:
    rows = copy.deepcopy(load_jsonl(MAPPING_GOLD_PATH))
    badcases = copy.deepcopy(load_jsonl(BADCASES_PATH))
    mutate(rows[0])

    with pytest.raises(AssertionError, match=message):
        run_contract_with_temp_data(monkeypatch, tmp_path, rows, badcases)


@pytest.mark.parametrize(
    "mutation",
    [
        "delete_standalone",
        "desync_standalone",
        "order",
        "duplicate_standalone_case_id",
        "duplicate_embedded_case_id",
        "badcase_type",
    ],
)
def test_contract_rejects_badcase_file_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
) -> None:
    rows = copy.deepcopy(load_jsonl(MAPPING_GOLD_PATH))
    badcases = copy.deepcopy(load_jsonl(BADCASES_PATH))
    if mutation == "delete_standalone":
        badcases.pop()
    elif mutation == "desync_standalone":
        badcases[0]["expected_behavior"] = "corrupted standalone behavior"
    elif mutation == "order":
        badcases.reverse()
    elif mutation == "duplicate_standalone_case_id":
        badcases[1]["case_id"] = badcases[0]["case_id"]
    elif mutation == "duplicate_embedded_case_id":
        duplicate_id = badcases[0]["case_id"]
        badcases[1]["case_id"] = duplicate_id
        rows[1]["known_badcases"][0]["case_id"] = duplicate_id
    else:
        badcases[0]["badcase_type"] = "unexpected_type"
        rows[0]["known_badcases"][0]["badcase_type"] = "unexpected_type"

    with pytest.raises(AssertionError, match="badcase"):
        run_contract_with_temp_data(monkeypatch, tmp_path, rows, badcases)


def test_real_world_mapping_gold_is_valid_jsonl() -> None:
    assert MAPPING_GOLD_PATH.is_file(), f"missing mapping gold: {MAPPING_GOLD_PATH}"
    assert BADCASES_PATH.is_file(), f"missing badcases: {BADCASES_PATH}"
    rows = load_jsonl(MAPPING_GOLD_PATH)
    standalone_badcases = load_jsonl(BADCASES_PATH)

    uir_by_doc_id: dict[str, dict[str, Any]] = {}
    for path in UIR_DIR.rglob("*.json"):
        uir = json.loads(path.read_text(encoding="utf-8"))
        uir_by_doc_id[uir["doc_id"]] = uir

    assert len(rows) == len(uir_by_doc_id)
    assert len(rows) >= 30
    doc_ids = [row.get("doc_id") for row in rows]
    assert len(set(doc_ids)) == len(rows)
    assert set(doc_ids) == set(uir_by_doc_id)
    assert {row.get("doc_type") for row in rows} == EXPECTED_DOC_TYPES

    schema_fields: dict[str, set[str]] = {}
    for path in SCHEMA_DIR.glob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_fields[schema["schema_id"]] = {
            field["field_id"] for field in schema["fields"]
        }

    for row in rows:
        doc_id = row["doc_id"]
        doc_type = row["doc_type"]
        assert doc_type == uir_by_doc_id[doc_id]["metadata"]["doc_type"]
        assert row.get("schema_id")
        assert row.get("template_id")
        assert_row_source_path_matches_uir(row, uir_by_doc_id[doc_id])

        if doc_type == "procurement_doc":
            assert row["schema_id"] == "procurement_doc"
            assert row["template_id"] == "procurement_doc_base_v1"
            allowed_target_fields = PROCUREMENT_TARGET_FIELDS
        else:
            assert row["schema_id"] == doc_type
            allowed_target_fields = schema_fields[doc_type]

        validate_mapping_row(row, uir_by_doc_id[doc_id], allowed_target_fields)

    embedded_badcases = [
        badcase for row in rows for badcase in row["known_badcases"]
    ]
    embedded_case_ids = [badcase["case_id"] for badcase in embedded_badcases]
    standalone_case_ids = [badcase.get("case_id") for badcase in standalone_badcases]
    assert len(set(embedded_case_ids)) == len(embedded_case_ids), (
        "embedded badcase case_id values must be unique"
    )
    assert len(set(standalone_case_ids)) == len(standalone_case_ids), (
        "standalone badcase case_id values must be unique"
    )
    assert {
        badcase["badcase_type"] for badcase in embedded_badcases
    } == EXPECTED_BADCASE_TYPES - {
        "semantic_role_confusion"
    }, "legacy embedded badcases must retain the original six-class contract"
    assert {
        badcase.get("badcase_type") for badcase in standalone_badcases
    } == EXPECTED_BADCASE_TYPES, "standalone badcases must cover the expanded taxonomy"
    assert all(badcase in standalone_badcases for badcase in embedded_badcases), (
        "every embedded badcase must be present in the standalone registry"
    )
    badcase_doc_ids = {badcase["doc_id"] for badcase in standalone_badcases}
    assert set(doc_ids) <= badcase_doc_ids, (
        "every real-world document must have standalone badcase coverage"
    )
    doc_order = {doc_id: index for index, doc_id in enumerate(doc_ids)}
    standalone_order = [
        doc_order[badcase["doc_id"]] for badcase in standalone_badcases
    ]
    assert standalone_order == sorted(standalone_order), (
        "standalone badcase rows must follow mapping-gold document order"
    )


def test_expanded_mapping_sources_are_nonempty_and_auditable() -> None:
    rows = load_jsonl(MAPPING_GOLD_PATH)
    uir_by_doc_id = {
        uir["doc_id"]: uir
        for path in UIR_DIR.rglob("*.json")
        if path.parent.name != "_rejected"
        for uir in [json.loads(path.read_text(encoding="utf-8"))]
    }
    generic_targets = {"title", "meeting_title", "content", "source", "source_url"}

    expanded_rows = [
        row
        for row in rows
        if any(
            "_inventory_" in badcase.get("case_id", "")
            for badcase in row["known_badcases"]
        )
    ]
    assert len(expanded_rows) == 14
    for row in expanded_rows:
        document = uir_by_doc_id[row["doc_id"]]
        type_specific_mappings = [
            mapping
            for mapping in row["expected_mappings"]
            if mapping["target_field"] not in generic_targets
        ]
        assert len(type_specific_mappings) >= 2, (
            f"{row['doc_id']}: requires at least two type-specific mappings"
        )
        for mapping in row["expected_mappings"]:
            if mapping["source_path"] == "blocks[*].text":
                continue
            values = source_path_values(document, mapping["source_path"])
            assert any(
                isinstance(value, str) and value.strip() for value in values
            ), (
                f"{row['doc_id']}: {mapping['target_field']} resolves to empty "
                f"content at {mapping['source_path']}"
            )
        for mapping in type_specific_mappings:
            values = source_path_values(document, mapping["source_path"])
            evidence = " | ".join(str(value) for value in values)
            assert mapping["source_name"] in evidence, (
                f"{row['doc_id']}: source_name {mapping['source_name']!r} is not "
                f"auditable from {mapping['source_path']}: {evidence!r}"
            )


def test_expanded_badcases_include_high_risk_case_per_doc_type() -> None:
    rows = load_jsonl(MAPPING_GOLD_PATH)
    expanded_rows = [
        row
        for row in rows
        if any(
            "_inventory_" in badcase.get("case_id", "")
            for badcase in row["known_badcases"]
        )
    ]

    for doc_type in EXPECTED_DOC_TYPES:
        badcases = [
            badcase
            for row in expanded_rows
            if row["doc_type"] == doc_type
            for badcase in row["known_badcases"]
        ]
        assert badcases, f"{doc_type}: missing expanded badcases"
        assert any(badcase["severity"] == "high" for badcase in badcases), (
            f"{doc_type}: expanded badcases require at least one high-risk case"
        )
