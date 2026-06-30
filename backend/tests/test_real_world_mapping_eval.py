import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
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
    assert known_badcases, f"{doc_id}: known_badcases must not be empty"
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
            lambda row: row["expected_mappings"].pop(),
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

    assert len(rows) == 16
    doc_ids = [row.get("doc_id") for row in rows]
    assert len(set(doc_ids)) == 16
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
    } == EXPECTED_BADCASE_TYPES, "embedded badcase types must match the six-class contract"
    assert {
        badcase.get("badcase_type") for badcase in standalone_badcases
    } == EXPECTED_BADCASE_TYPES, "standalone badcase types must match the six-class contract"
    assert standalone_badcases == embedded_badcases, (
        "standalone badcases must exactly match deterministic embedded flattening"
    )
