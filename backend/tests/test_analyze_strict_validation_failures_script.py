import importlib.util
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "analyze_strict_validation_failures.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_strict_validation_failures",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_package(
    path: Path,
    *,
    doc_id: str,
    schema_id: str,
    passed: bool,
    required_missing: list[str],
    review_targets: list[str],
) -> None:
    issues = [
        {
            "code": "required_field_missing",
            "field_id": field_id,
            "level": "error",
            "message": "Required field is missing.",
        }
        for field_id in required_missing
    ]
    mapping = {
        "summary": {
            "review_required_count": len(review_targets),
            "required_unmapped_count": len(required_missing),
        },
        "review_required_items": [
            {
                "target_field_id": target,
                "method": "fuzzy",
                "risk_flags": ["fuzzy_match"],
            }
            for target in review_targets
        ],
        "unmapped": [
            {
                "target_field_id": field_id,
                "required": True,
                "risk_flags": ["required_field_unmapped"],
            }
            for field_id in required_missing
        ],
    }
    transform = {
        "issues": [
            {
                "code": "date_parse_failed",
                "field_id": "publish_date",
            }
        ]
        if not passed
        else []
    }
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "metadata.json",
            json.dumps({"doc_id": doc_id, "schema_id": schema_id}),
        )
        archive.writestr(
            "validation_report.json",
            json.dumps({"passed": passed, "issues": issues}),
        )
        archive.writestr("mapping_report.json", json.dumps(mapping))
        archive.writestr("transform_report.json", json.dumps(transform))


def test_analyzer_aggregates_failures_by_doc_type_and_field(tmp_path: Path) -> None:
    module = load_module()
    packages = tmp_path / "packages"
    packages.mkdir()
    write_package(
        packages / "policy.zip",
        doc_id="policy-1",
        schema_id="policy_doc",
        passed=False,
        required_missing=["issuer", "publish_date"],
        review_targets=["effective_date"],
    )
    write_package(
        packages / "meeting.zip",
        doc_id="meeting-1",
        schema_id="meeting_doc",
        passed=True,
        required_missing=[],
        review_targets=["attendees"],
    )

    report = module.analyze(packages_root=packages)

    assert report["summary"] == {
        "package_count": 2,
        "validation_pass_count": 1,
        "validation_fail_count": 1,
        "required_missing_count": 2,
        "review_required_count": 2,
    }
    assert report["failures_by_doc_type"] == {"policy_doc": 1}
    assert report["required_missing_by_field"] == {"issuer": 1, "publish_date": 1}
    assert report["review_required_by_field"] == {
        "attendees": 1,
        "effective_date": 1,
    }
    assert report["failure_categories"]["date_parse_failed"] == 1
    assert report["items"][0]["doc_id"] == "meeting-1"
    assert report["items"][1]["doc_id"] == "policy-1"


def test_analyzer_writes_json_and_markdown(tmp_path: Path) -> None:
    module = load_module()
    packages = tmp_path / "packages"
    packages.mkdir()
    write_package(
        packages / "policy.zip",
        doc_id="policy-1",
        schema_id="policy_doc",
        passed=False,
        required_missing=["issuer"],
        review_targets=["effective_date"],
    )
    json_path = tmp_path / "analysis.json"
    markdown_path = tmp_path / "analysis.md"

    report = module.run(
        packages_root=packages,
        gold_path=None,
        out_path=json_path,
        markdown_path=markdown_path,
    )

    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"] == report["summary"]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Strict Validation Gap Analysis" in markdown
    assert "| policy_doc | 1 |" in markdown
    assert "| issuer | 1 |" in markdown
