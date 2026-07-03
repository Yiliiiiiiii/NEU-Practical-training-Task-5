import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analyze_non_procurement_gaps.py"
DOC_TYPES = ("general_doc", "meeting_doc", "policy_doc")
REPORT_KEYS = {
    "summary",
    "top_missing_required_fields",
    "top_review_required_fields",
    "candidate_extraction_gaps",
    "alias_gaps",
    "regex_gaps",
    "schema_gaps",
    "transform_gaps",
    "badcase_sensitive_items",
    "recommended_plan",
}
GAP_KEYS = {
    "doc_type",
    "doc_id",
    "target_field",
    "gap_type",
    "count",
    "candidate_source_names",
    "candidate_value_samples",
    "source_block_ids",
    "review_required_reason",
    "recommended_action",
}


def load_script():
    scripts_dir = str(SCRIPT.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(
        "analyze_non_procurement_gaps",
        SCRIPT,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_package(
    package_dir: Path,
    *,
    doc_id: str,
    doc_type: str,
    missing: list[str] | None = None,
    mappings: list[dict[str, object]] | None = None,
    reviews: list[dict[str, object]] | None = None,
    unmapped: list[dict[str, object]] | None = None,
    validation_issues: list[dict[str, object]] | None = None,
    blocks: list[dict[str, object]] | None = None,
    passed: bool = False,
) -> Path:
    payloads = {
        "metadata.json": {"doc_id": doc_id, "doc_type": doc_type},
        "mapping_report.json": {
            "mappings": mappings or [],
            "review_required_items": reviews or [],
            "unmapped": unmapped or [],
        },
        "validation_report.json": {
            "passed": passed,
            "missing_required_fields": missing or [],
            "issues": validation_issues or [],
        },
        "content.json": {"blocks": blocks or []},
        "canonical.json": {"doc_id": doc_id},
    }
    for filename, payload in payloads.items():
        write_json(package_dir / filename, payload)
    return package_dir


def gold_row(
    doc_id: str,
    doc_type: str,
    target_field: str,
    *,
    source_name: str = "expected source",
) -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "doc_type": doc_type,
        "expected_mappings": [
            {
                "source_name": source_name,
                "source_path": "blocks[0].text",
                "target_field": target_field,
            }
        ],
        "expected_review_required": [],
        "known_badcases": [],
        "relevant_source_block_ids": [f"{doc_id}_b001"],
    }


def test_recursive_discovery_finds_complete_packages_and_ignores_partial_dirs(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    root = tmp_path / "packages"
    complete = make_package(
        root / "arbitrary" / "depth" / "doc",
        doc_id="doc",
        doc_type="general_doc",
    )
    write_json(root / "partial" / "metadata.json", {"doc_id": "partial"})

    assert analyzer.discover_package_dirs(root) == [complete]


def test_discovery_and_analysis_accept_exported_zip_packages(tmp_path: Path) -> None:
    analyzer = load_script()
    root = tmp_path / "packages"
    package_dir = make_package(
        tmp_path / "source-package",
        doc_id="zip-doc",
        doc_type="general_doc",
        passed=True,
    )
    zip_path = root / "zip-doc.zip"
    zip_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in sorted(package_dir.iterdir()):
            archive.write(path, path.name)

    packages, diagnostics = analyzer.discover_package_inventory(root)
    report = analyzer.analyze_packages(
        packages,
        [gold_row("zip-doc", "general_doc", "title")],
        [],
        top_n=10,
        discovery_diagnostics=diagnostics,
    )

    assert packages == [zip_path]
    assert diagnostics["complete_packages_discovered"] == 1
    assert report["summary"]["documents_total"] == 1


def test_analysis_filters_procurement_and_contract_packages(tmp_path: Path) -> None:
    analyzer = load_script()
    root = tmp_path / "packages"
    for doc_type in (*DOC_TYPES, "procurement_doc", "contract_doc"):
        make_package(
            root / doc_type,
            doc_id=f"{doc_type}_001",
            doc_type=doc_type,
            passed=True,
        )

    report = analyzer.analyze_packages(
        analyzer.discover_package_dirs(root),
        gold_rows=[],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["summary"]["documents_total"] == 3
    assert set(report["summary"]["by_doc_type"]) == set(DOC_TYPES)
    assert {item["doc_type"] for key in REPORT_KEYS - {"summary"} for item in report[key]} <= set(
        DOC_TYPES
    )


def test_candidate_not_extracted_and_badcase_sensitive_take_precedence(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    root = tmp_path / "packages"
    candidate = make_package(
        root / "candidate",
        doc_id="candidate",
        doc_type="general_doc",
        missing=["issuer"],
        unmapped=[
            {
                "target_field_id": "issuer",
                "required": True,
                "risk_flags": ["required_unmapped"],
            }
        ],
        blocks=[{"id": "candidate_b001", "text": "Ordinary body text."}],
    )
    badcase = make_package(
        root / "badcase",
        doc_id="badcase",
        doc_type="policy_doc",
        missing=["publish_date"],
        reviews=[
            {
                "source_name": "generated date",
                "target_field": "publish_date",
                "status": "badcase_blocked",
                "review_required_reason": "Forbidden ambiguous date mapping.",
            }
        ],
        blocks=[
            {
                "id": "badcase_b001",
                "text": "Publication date: 2025-01-02",
            }
        ],
    )
    rows = [
        gold_row("candidate", "general_doc", "issuer"),
        gold_row(
            "badcase",
            "policy_doc",
            "publish_date",
            source_name="generated date",
        ),
    ]
    badcases = [
        {
            "case_id": "ambiguous_date",
            "doc_id": "badcase",
            "forbidden_auto_mapping": {
                "source_name": "generated date",
                "target_field": "publish_date",
            },
        }
    ]

    report = analyzer.analyze_packages(
        [candidate, badcase],
        gold_rows=rows,
        badcase_rows=badcases,
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["candidate_extraction_gaps"][0]["gap_type"] == ("candidate_not_extracted")
    assert report["candidate_extraction_gaps"][0]["recommended_action"] == ("enhance_candidate")
    assert report["badcase_sensitive_items"][0]["doc_id"] == "badcase"
    assert report["badcase_sensitive_items"][0]["gap_type"] == "badcase_sensitive"
    assert report["badcase_sensitive_items"][0]["recommended_action"] == ("keep_review_required")
    assert not any(
        item["doc_id"] == "badcase"
        for key in (
            "candidate_extraction_gaps",
            "alias_gaps",
            "regex_gaps",
            "schema_gaps",
            "transform_gaps",
        )
        for item in report[key]
    )


def test_accepted_forbidden_pair_is_reported_as_badcase_sensitive(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "badcase-accepted",
        doc_id="badcase-accepted",
        doc_type="policy_doc",
        mappings=[
            {
                "source_name": "generated date",
                "target_field": "publish_date",
                "status": "accepted",
            }
        ],
    )
    gold = gold_row(
        "badcase-accepted",
        "policy_doc",
        "publish_date",
        source_name="generated date",
    )
    badcase = {
        "doc_id": "badcase-accepted",
        "forbidden_auto_mapping": {
            "source_name": "generated date",
            "target_field": "publish_date",
        },
    }

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold],
        badcase_rows=[badcase],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["summary"]["badcase_violation_count"] == 1
    assert report["badcase_sensitive_items"][0]["target_field"] == "publish_date"


def test_transform_type_error_classification(tmp_path: Path) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "transform",
        doc_id="transform",
        doc_type="meeting_doc",
        missing=["meeting_date"],
        reviews=[
            {
                "source_name": "meeting date",
                "source_value": "January 44",
                "target_field_id": "meeting_date",
                "review_required_reason": "Type mismatch during date transform.",
            }
        ],
        validation_issues=[
            {
                "field": "meeting_date",
                "code": "type_error",
                "message": "Expected a valid date.",
            }
        ],
    )

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold_row("transform", "meeting_doc", "meeting_date")],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["transform_gaps"] == [
        {
            **report["transform_gaps"][0],
            "doc_id": "transform",
            "target_field": "meeting_date",
            "gap_type": "transform_type_error",
            "recommended_action": "enhance_transform",
        }
    ]


def test_strict_pass_uses_mapping_facts_not_validation_boolean(tmp_path: Path) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "strict",
        doc_id="strict",
        doc_type="general_doc",
        passed=False,
        mappings=[
            {
                "source_name": "title",
                "target_field": "title",
                "status": "accepted",
            },
            {
                "source_name": "document text",
                "target_field": "content",
                "status": "accepted",
            },
        ],
    )
    gold = {
        "doc_id": "strict",
        "doc_type": "general_doc",
        "expected_mappings": [
            {"source_name": "title", "target_field": "title"},
            {"source_name": "document text", "target_field": "content"},
        ],
        "expected_review_required": [],
        "known_badcases": [],
    }

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["summary"]["strict_pass_count"] == 1


def test_missing_root_and_malformed_required_json_name_the_path(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    missing_root = tmp_path / "missing"
    with pytest.raises(ValueError, match=str(missing_root).replace("\\", "\\\\")):
        analyzer.discover_package_dirs(missing_root)

    package = make_package(
        tmp_path / "bad-json",
        doc_id="bad-json",
        doc_type="general_doc",
    )
    malformed = package / "mapping_report.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping_report.json"):
        analyzer.analyze_packages(
            [package],
            gold_rows=[],
            badcase_rows=[],
            doc_types=DOC_TYPES,
            top_n=30,
        )

    write_json(malformed, [])
    with pytest.raises(ValueError, match="mapping_report.json"):
        analyzer.analyze_packages(
            [package],
            gold_rows=[],
            badcase_rows=[],
            doc_types=DOC_TYPES,
            top_n=30,
        )


def test_json_report_and_gap_items_follow_contract(tmp_path: Path) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "doc",
        doc_id="doc",
        doc_type="general_doc",
        missing=["issuer"],
    )

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold_row("doc", "general_doc", "issuer")],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert set(report) == REPORT_KEYS
    assert {
        "documents_total",
        "strict_pass_count",
        "review_required_count",
        "required_missing_count",
        "average_recall",
        "badcase_violation_count",
        "by_doc_type",
    } <= set(report["summary"])
    assert set(report["summary"]["by_doc_type"]) == set(DOC_TYPES)
    for key in REPORT_KEYS - {"summary"}:
        for item in report[key]:
            assert GAP_KEYS <= set(item), key


def test_markdown_contains_required_headings(tmp_path: Path) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "doc",
        doc_id="doc",
        doc_type="general_doc",
        passed=True,
    )
    report = analyzer.analyze_packages(
        [package],
        gold_rows=[],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    headings = {
        line[3:] for line in analyzer.render_markdown(report).splitlines() if line.startswith("## ")
    }

    assert headings == {
        "Summary",
        "By Document Type",
        "Top Missing Required Fields",
        "Top Review-required Fields",
        "Candidate Extraction Gaps",
        "Alias Gaps",
        "Regex Rule Gaps",
        "Schema Required-field Gaps",
        "Transform / Type Normalization Gaps",
        "Badcase-sensitive Items",
        "Recommended Fix Plan",
        "Do-not-auto-accept List",
    }


def test_ordering_and_top_n_are_deterministic(tmp_path: Path) -> None:
    analyzer = load_script()
    packages = [
        make_package(
            tmp_path / doc_id,
            doc_id=doc_id,
            doc_type="general_doc",
            missing=["issuer"],
        )
        for doc_id in ("z-doc", "a-doc", "m-doc")
    ]
    rows = [gold_row(doc_id, "general_doc", "issuer") for doc_id in ("z-doc", "a-doc", "m-doc")]

    first = analyzer.analyze_packages(
        list(reversed(packages)),
        gold_rows=list(reversed(rows)),
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=2,
    )
    second = analyzer.analyze_packages(
        packages,
        gold_rows=rows,
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=2,
    )

    assert first == second
    assert first["candidate_extraction_gaps"] == [
        {
            **first["candidate_extraction_gaps"][0],
            "doc_id": "a-doc",
            "count": 3,
        }
    ]
    assert all(len(first[key]) <= 2 for key in REPORT_KEYS - {"summary"})


def test_doc_type_parser_rejects_unsupported_values() -> None:
    analyzer = load_script()

    assert analyzer.parse_doc_types("general_doc,meeting_doc") == (
        "general_doc",
        "meeting_doc",
    )
    with pytest.raises(ValueError, match="unsupported_doc"):
        analyzer.parse_doc_types("general_doc,unsupported_doc")


def test_generic_metadata_is_not_an_alias_or_recommended(tmp_path: Path) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "generic",
        doc_id="generic",
        doc_type="general_doc",
        reviews=[
            {
                "source_name": "extraction_version",
                "source_path": "$.metadata.extraction_version",
                "source_value": "0.1.0",
                "source_blocks": [],
                "target_field": "application_conditions",
                "status": "review_required",
                "method": "fuzzy",
            }
        ],
    )

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[
            {
                "doc_id": "generic",
                "doc_type": "general_doc",
                "expected_mappings": [
                    {
                        "source_name": "extraction_version",
                        "source_path": "$.metadata.extraction_version",
                        "target_field": "application_conditions",
                    }
                ],
                "expected_review_required": [],
                "known_badcases": [],
            }
        ],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["alias_gaps"] == []
    assert not any(
        item["candidate_source_names"] == ["extraction_version"]
        for item in report["recommended_plan"]
    )


def test_forbidden_gold_evidence_without_current_candidate_is_badcase_sensitive(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "forbidden-gold",
        doc_id="forbidden-gold",
        doc_type="policy_doc",
        blocks=[
            {
                "id": "forbidden-gold_b001",
                "text": "生成日期：2025-03-18",
            }
        ],
    )
    gold = {
        "doc_id": "forbidden-gold",
        "doc_type": "policy_doc",
        "expected_mappings": [],
        "expected_review_required": [
            {
                "source_name": "生成日期",
                "source_path": "blocks[0].text",
                "target_field": "publish_date",
            }
        ],
        "known_badcases": [],
    }
    badcase = {
        "doc_id": "forbidden-gold",
        "forbidden_auto_mapping": {
            "source_name": "生成日期",
            "target_field": "publish_date",
        },
    }

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold],
        badcase_rows=[badcase],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["badcase_sensitive_items"][0]["candidate_source_names"] == [
        "生成日期"
    ]
    assert report["badcase_sensitive_items"][0]["source_block_ids"] == [
        "forbidden-gold_b001"
    ]
    assert not any(
        item["target_field"] == "publish_date"
        for item in report["recommended_plan"]
    )


def test_document_level_gold_blocks_do_not_become_target_provenance(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "provenance",
        doc_id="provenance",
        doc_type="general_doc",
        blocks=[{"id": "context-only", "text": "Document context"}],
    )
    gold = gold_row("provenance", "general_doc", "issuer")
    expected = gold["expected_mappings"][0]
    assert isinstance(expected, dict)
    expected["source_path"] = "metadata.issuer"
    gold["relevant_source_block_ids"] = ["context-only"]

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    assert report["candidate_extraction_gaps"][0]["source_block_ids"] == []


def test_gap_frequency_aggregation_drives_top_n(tmp_path: Path) -> None:
    analyzer = load_script()
    packages = []
    rows = []
    for doc_id, target in (
        ("issuer-a", "issuer"),
        ("issuer-b", "issuer"),
        ("issuer-c", "issuer"),
        ("date-a", "publish_date"),
        ("date-b", "publish_date"),
    ):
        packages.append(
            make_package(
                tmp_path / doc_id,
                doc_id=doc_id,
                doc_type="policy_doc",
                missing=[target],
            )
        )
        rows.append(gold_row(doc_id, "policy_doc", target))

    report = analyzer.analyze_packages(
        list(reversed(packages)),
        gold_rows=list(reversed(rows)),
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=1,
    )

    top = report["candidate_extraction_gaps"]
    assert len(top) == 1
    assert top[0]["target_field"] == "issuer"
    assert top[0]["count"] == 3
    assert top[0]["document_ids"] == ["issuer-a", "issuer-b", "issuer-c"]
    assert report["recommended_plan"][0]["target_field"] == "issuer"


def test_top_field_frequency_combines_gap_classifications(tmp_path: Path) -> None:
    analyzer = load_script()
    candidate = make_package(
        tmp_path / "candidate",
        doc_id="candidate",
        doc_type="policy_doc",
        missing=["issuer"],
        reviews=[
            {
                "source_name": "extraction_version",
                "source_path": "$.metadata.extraction_version",
                "target_field": "issuer",
            }
        ],
    )
    transform = make_package(
        tmp_path / "transform",
        doc_id="transform",
        doc_type="policy_doc",
        missing=["issuer"],
        reviews=[
            {
                "source_name": "issuer",
                "target_field": "issuer",
                "review_required_reason": "Transform type mismatch.",
            }
        ],
    )

    report = analyzer.analyze_packages(
        [transform, candidate],
        gold_rows=[],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    for key in ("top_missing_required_fields", "top_review_required_fields"):
        assert len(report[key]) == 1
        assert report[key][0]["target_field"] == "issuer"
        assert report[key][0]["count"] == 2
        assert report[key][0]["document_ids"] == ["candidate", "transform"]
        assert report[key][0]["gap_types"] == [
            "schema_too_strict",
            "transform_type_error",
        ]


@pytest.mark.parametrize(
    ("filename", "mutate", "expected_path"),
    [
        (
            "mapping_report.json",
            lambda value: value.update({"mappings": {}}),
            r"mapping_report\.json\.mappings",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"review_required_items": [1]}),
            r"mapping_report\.json\.review_required_items\[0\]",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"unmapped": "issuer"}),
            r"mapping_report\.json\.unmapped",
        ),
        (
            "validation_report.json",
            lambda value: value.update({"passed": "false"}),
            r"validation_report\.json\.passed",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"summary": {"mapping_recall": "0.5"}}),
            r"mapping_report\.json\.summary\.mapping_recall",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"review_evidence": {}}),
            r"mapping_report\.json\.review_evidence",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"review_evidence": ["bad"]}),
            r"mapping_report\.json\.review_evidence\[0\]",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"candidates": "bad"}),
            r"mapping_report\.json\.candidates",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"mapping_candidates": [1]}),
            r"mapping_report\.json\.mapping_candidates\[0\]",
        ),
        (
            "validation_report.json",
            lambda value: value.update({"issues": {}}),
            r"validation_report\.json\.issues",
        ),
        (
            "validation_report.json",
            lambda value: value.update({"errors": ["bad"]}),
            r"validation_report\.json\.errors\[0\]",
        ),
        (
            "validation_report.json",
            lambda value: value.update({"validation_errors": [False]}),
            r"validation_report\.json\.validation_errors\[0\]",
        ),
        (
            "validation_report.json",
            lambda value: value.update({"missing_required_fields": {}}),
            r"validation_report\.json\.missing_required_fields",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"required_missing": [1]}),
            r"mapping_report\.json\.required_missing\[0\]",
        ),
        (
            "mapping_report.json",
            lambda value: value.update({"unmapped_required_fields": "issuer"}),
            r"mapping_report\.json\.unmapped_required_fields",
        ),
        (
            "mapping_report.json",
            lambda value: value.update(
                {
                    "mappings": [
                        {
                            "target_field": "issuer",
                            "risk_flags": {},
                        }
                    ]
                }
            ),
            r"mapping_report\.json\.mappings\[0\]\.risk_flags",
        ),
        (
            "mapping_report.json",
            lambda value: value.update(
                {
                    "review_required_items": [
                        {
                            "target_field": "issuer",
                            "source_field": "bad",
                        }
                    ]
                }
            ),
            r"mapping_report\.json\.review_required_items\[0\]\.source_field",
        ),
        (
            "mapping_report.json",
            lambda value: value.update(
                {
                    "candidates": [
                        {
                            "target_field_candidates": {},
                        }
                    ]
                }
            ),
            r"mapping_report\.json\.candidates\[0\]\.target_field_candidates",
        ),
        (
            "content.json",
            lambda value: value.update({"blocks": {}}),
            r"content\.json\.blocks",
        ),
        (
            "content.json",
            lambda value: value.update({"blocks": ["bad"]}),
            r"content\.json\.blocks\[0\]",
        ),
        (
            "content.json",
            lambda value: value.update({"document": []}),
            r"content\.json\.document",
        ),
    ],
)
def test_malformed_nested_report_shapes_are_path_specific(
    tmp_path: Path,
    filename: str,
    mutate,
    expected_path: str,
) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "malformed",
        doc_id="malformed",
        doc_type="general_doc",
    )
    path = package / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    write_json(path, payload)

    with pytest.raises(ValueError, match=expected_path):
        analyzer.analyze_packages(
            [package],
            gold_rows=[],
            badcase_rows=[],
            doc_types=DOC_TYPES,
            top_n=30,
        )


def test_cli_returns_nonzero_for_malformed_nested_report(tmp_path: Path) -> None:
    package = make_package(
        tmp_path / "packages" / "malformed",
        doc_id="malformed",
        doc_type="general_doc",
    )
    write_json(
        package / "validation_report.json",
        {"passed": False, "issues": "not-an-array"},
    )
    gold = tmp_path / "gold.jsonl"
    badcases = tmp_path / "badcases.jsonl"
    gold.write_text("", encoding="utf-8")
    badcases.write_text("", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--packages-root",
            str(tmp_path / "packages"),
            "--gold",
            str(gold),
            "--badcases",
            str(badcases),
            "--out",
            str(tmp_path / "out.json"),
            "--markdown",
            str(tmp_path / "out.md"),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert "validation_report.json.issues" in result.stderr


@pytest.mark.parametrize(
    ("gold_rows", "badcase_rows", "expected_path"),
    [
        (
            [{"doc_id": "doc", "expected_mappings": {}}],
            [],
            r"gold_rows\[0\]\.expected_mappings",
        ),
        (
            [{"doc_id": "doc", "expected_review_required": ["bad"]}],
            [],
            r"gold_rows\[0\]\.expected_review_required\[0\]",
        ),
        (
            [{"doc_id": "doc", "known_badcases": "bad"}],
            [],
            r"gold_rows\[0\]\.known_badcases",
        ),
        (
            [],
            [{"doc_id": "doc", "forbidden_auto_mapping": "bad"}],
            r"badcase_rows\[0\]\.forbidden_auto_mapping",
        ),
    ],
)
def test_malformed_gold_and_badcase_shapes_are_path_specific(
    tmp_path: Path,
    gold_rows: list[dict[str, object]],
    badcase_rows: list[dict[str, object]],
    expected_path: str,
) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "doc",
        doc_id="doc",
        doc_type="general_doc",
    )

    with pytest.raises(ValueError, match=expected_path):
        analyzer.analyze_packages(
            [package],
            gold_rows=gold_rows,
            badcase_rows=badcase_rows,
            doc_types=DOC_TYPES,
            top_n=30,
        )


def test_duplicate_target_gold_keeps_each_unmatched_source_diagnosable(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    package = make_package(
        tmp_path / "duplicate-gold",
        doc_id="duplicate-gold",
        doc_type="policy_doc",
        mappings=[
            {
                "source_name": "signed date",
                "source_path": "blocks[0].text",
                "target_field": "publish_date",
                "status": "accepted",
            }
        ],
        blocks=[
            {"id": "signed", "text": "Signed date: 2025-01-03"},
            {"id": "web", "text": "Published: 2025-01-08"},
        ],
    )
    gold = {
        "doc_id": "duplicate-gold",
        "doc_type": "policy_doc",
        "expected_mappings": [
            {
                "source_name": "signed date",
                "source_path": "blocks[0].text",
                "target_field": "publish_date",
            },
            {
                "source_name": "web publish date",
                "source_path": "blocks[1].text",
                "target_field": "publish_date",
            },
        ],
        "expected_review_required": [],
        "known_badcases": [],
    }

    report = analyzer.analyze_packages(
        [package],
        gold_rows=[gold],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
    )

    item = report["candidate_extraction_gaps"][0]
    assert item["candidate_source_names"] == ["web publish date"]
    assert item["source_block_ids"] == ["web"]


def test_diagnostics_count_complete_analyzed_ignored_and_incomplete_packages(
    tmp_path: Path,
) -> None:
    analyzer = load_script()
    root = tmp_path / "packages"
    make_package(
        root / "supported",
        doc_id="supported",
        doc_type="general_doc",
    )
    make_package(
        root / "ignored",
        doc_id="ignored",
        doc_type="procurement_doc",
    )
    write_json(root / "incomplete" / "metadata.json", {"doc_id": "incomplete"})

    packages, discovery = analyzer.discover_package_inventory(root)
    report = analyzer.analyze_packages(
        packages,
        gold_rows=[],
        badcase_rows=[],
        doc_types=DOC_TYPES,
        top_n=30,
        discovery_diagnostics=discovery,
    )

    assert report["summary"]["diagnostics"] == {
        "complete_packages_discovered": 2,
        "packages_analyzed": 1,
        "ignored_document_type_count": 1,
        "ignored_document_types": {"procurement_doc": 1},
        "incomplete_package_count": 1,
    }
