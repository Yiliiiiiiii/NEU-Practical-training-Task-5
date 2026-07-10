"""Evaluate SchemaPack contracts, examples, assertions, and badcases."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.services.schema_pack_contract_validator import (  # noqa: E402
    SchemaPackContractValidator,
)
from app.services.schema_pack_service import SchemaPackService  # noqa: E402
from app.services.topic5_conversion_service import Topic5ConversionService  # noqa: E402


DEFAULT_EXAMPLES = ROOT / "schema_packs" / "examples"
DEFAULT_JSON = ROOT / "reports" / "schema_pack_contract_all.json"
DEFAULT_MD = ROOT / "reports" / "schema_pack_contract_all.md"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _mapping_template(payload: dict[str, Any], display_name: str) -> MappingTemplate:
    regex_rules = [
        {
            key: item[key]
            for key in ("target_field_id", "pattern", "group")
            if key in item
        }
        for item in payload.get("regex_rules", [])
        if isinstance(item, dict)
    ]
    return MappingTemplate.model_validate(
        {
            "template_id": payload.get("template_id"),
            "schema_id": payload.get("schema_id"),
            "name": payload.get("name") or display_name,
            "version": payload.get("version"),
            "aliases": payload.get("aliases", {}),
            "regex_rules": regex_rules,
            "transform_rules": payload.get("transform_rules", []),
            "defaults": payload.get("defaults", {}),
            "enum_maps": payload.get("enum_maps", {}),
        }
    )


def _build_request(
    service: SchemaPackService,
    schema_pack_id: str,
    uir: dict[str, Any],
    fixture_options: dict[str, Any] | None = None,
) -> Topic5ConvertRequest:
    manifest = service.load_manifest(schema_pack_id)
    mapping_payload = service.load_mapping_rules(schema_pack_id)
    options = {
        "mapping_mode": manifest.execution.default_mapping_mode,
        "enable_llm_fallback": manifest.execution.allow_llm_fallback,
        "include_assertion_report_in_package": (
            manifest.execution.include_assertion_report_in_package
        ),
        "negative_pairs": mapping_payload.get("negative_pairs", []),
        "thresholds": mapping_payload.get("thresholds", {}),
        "candidate_profile": mapping_payload.get("candidate_hints", {}),
        "schema_pack_id": manifest.schema_pack_id,
        "schema_pack_version": manifest.schema_pack_version,
        "no_code_schema_pack_onboarding": True,
    }
    options.update(fixture_options or {})
    assertions = service.load_output_assertions(schema_pack_id)
    return Topic5ConvertRequest.model_validate(
        {
            "uir": uir,
            "target_schema": service.load_target_schema(schema_pack_id),
            "mapping_rules": _mapping_template(
                mapping_payload,
                manifest.display_name,
            ).model_dump(mode="json"),
            "metadata_template": service.load_metadata_template(schema_pack_id),
            "content_organization": service.load_content_org(schema_pack_id),
            "output_assertions": (
                assertions.model_dump(mode="json") if assertions is not None else None
            ),
            "options": options,
        }
    )


def _matches_subset(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches_subset(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and actual == expected
    return actual == expected


def _result_statuses(report: dict[str, Any] | None) -> dict[str, str]:
    if not report:
        return {}
    return {
        str(item["assertion_id"]): str(item["status"])
        for item in report.get("results", [])
        if isinstance(item, dict) and item.get("assertion_id")
    }


def _failed_result_severities(report: dict[str, Any] | None) -> dict[str, str]:
    if not report:
        return {}
    return {
        str(item["assertion_id"]): str(item["severity"])
        for item in report.get("results", [])
        if isinstance(item, dict)
        and item.get("assertion_id")
        and item.get("status") == "failed"
    }


def _convert(
    service: SchemaPackService,
    schema_pack_id: str,
    uir: dict[str, Any],
    *,
    verify_package: bool,
    fixture_options: dict[str, Any] | None = None,
):
    request = _build_request(service, schema_pack_id, uir, fixture_options)
    with tempfile.TemporaryDirectory(prefix=f"schema_pack_{schema_pack_id}_") as tmp:
        return Topic5ConversionService(tmp).convert(
            request,
            create_package=verify_package,
        )


def evaluate_pack(pack_dir: Path, *, verify_package: bool) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    contract = SchemaPackContractValidator().validate(pack_dir)
    schema_pack_id = str(contract.get("schema_pack_id") or pack_dir.name)
    item: dict[str, Any] = {
        "status": "failed",
        "schema_pack_id": schema_pack_id,
        "schema_pack_version": contract.get("schema_pack_version"),
        "contract_valid": contract["status"] == "passed",
        "positive_examples_passed": 0,
        "positive_examples_total": 0,
        "badcases_passed": 0,
        "badcases_total": 0,
        "assertion_errors": 0,
        "unexpected_assertion_failures": [],
        "package_verifier_passed": None,
        "package_with_assertion_report_verified": None,
        "package_without_assertion_report_verified": None,
        "contract_errors": contract["errors"],
    }
    if contract["status"] != "passed":
        return item

    service = SchemaPackService(pack_dir.parent.parent)
    package_results: list[tuple[bool, bool]] = []
    examples_dir = pack_dir / "examples"
    for request_path in sorted(examples_dir.glob("example_*_request.json")):
        item["positive_examples_total"] += 1
        fixture = _read_json(request_path)
        uir = _read_json(examples_dir / str(fixture["uir_path"]))
        response = _convert(
            service,
            schema_pack_id,
            uir,
            verify_package=verify_package and bool(fixture.get("create_package", True)),
            fixture_options=fixture.get("options"),
        )
        expected_content = _read_json(
            request_path.with_name(request_path.name.replace("_request", "_expected_content"))
        )
        expected_assertions = _read_json(
            request_path.with_name(
                request_path.name.replace("_request", "_expected_assertions")
            )
        )
        statuses = _result_statuses(response.conversion_assertion_report)
        expected_statuses = expected_assertions.get("expected_results", {})
        positive_passed = (
            response.status == "completed"
            and _matches_subset(response.content_json, expected_content)
            and statuses == expected_statuses
            and bool(response.conversion_assertion_report)
            and response.conversion_assertion_report.get("passed")
                == expected_assertions.get("passed")
            and response.conversion_assertion_report.get("error_count")
                == expected_assertions.get("error_count")
            and response.conversion_assertion_report.get("warning_count")
                == expected_assertions.get("warning_count")
        )
        if positive_passed:
            item["positive_examples_passed"] += 1
        else:
            failed_ids = sorted(
                assertion_id
                for assertion_id, status in statuses.items()
                if status == "failed"
            )
            item["unexpected_assertion_failures"].extend(
                f"examples/{request_path.name}:{assertion_id}"
                for assertion_id in failed_ids or ["positive_example_mismatch"]
            )
        item["assertion_errors"] += int(
            (response.conversion_assertion_report or {}).get("error_count", 0)
        )
        if verify_package:
            verifier_passed = bool(
                response.verifier_report and response.verifier_report.get("passed")
            )
            assertion_report_packaged = bool(
                response.manifest
                and any(
                    entry.get("path") == "reports/conversion_assertion_report.json"
                    and entry.get("required") is False
                    and entry.get("role") == "conversion_assertion_report"
                    and entry.get("media_type") == "application/json"
                    for entry in response.manifest.get("files", [])
                    if isinstance(entry, dict)
                )
            )
            package_results.append((verifier_passed, assertion_report_packaged))

    badcases_dir = pack_dir / "badcases"
    for uir_path in sorted(badcases_dir.glob("badcase_*_uir.json")):
        item["badcases_total"] += 1
        response = _convert(
            service,
            schema_pack_id,
            _read_json(uir_path),
            verify_package=False,
        )
        expected_path = uir_path.with_name(
            uir_path.name.replace("_uir", "_expected_assertions")
        )
        expected = _read_json(expected_path)
        expected_ids = set(expected.get("expected_failed_assertion_ids", []))
        expected_severities = {
            str(assertion_id): str(severity)
            for assertion_id, severity in expected.get("expected_severities", {}).items()
        }
        statuses = _result_statuses(response.conversion_assertion_report)
        actual_ids = {
            assertion_id
            for assertion_id, status in statuses.items()
            if status == "failed"
        }
        actual_severities = _failed_result_severities(
            response.conversion_assertion_report
        )
        severity_matches = actual_severities == expected_severities
        if actual_ids == expected_ids and severity_matches:
            item["badcases_passed"] += 1
        else:
            missing = sorted(expected_ids - actual_ids)
            unexpected = sorted(actual_ids - expected_ids)
            item["unexpected_assertion_failures"].extend(
                f"badcases/{uir_path.name}:{assertion_id}"
                for assertion_id in [*missing, *unexpected]
            )
            item["unexpected_assertion_failures"].extend(
                f"badcases/{uir_path.name}:{assertion_id}:"
                f"expected_severity={expected_severities.get(assertion_id)}:"
                f"actual_severity={actual_severities.get(assertion_id)}"
                for assertion_id in sorted(
                    set(expected_severities) | set(actual_severities)
                )
                if actual_severities.get(assertion_id)
                != expected_severities.get(assertion_id)
            )

    if item["positive_examples_total"] == 0:
        item["unexpected_assertion_failures"].append(
            "examples:no_positive_fixtures"
        )
    if item["badcases_total"] == 0:
        item["unexpected_assertion_failures"].append("badcases:no_badcase_fixtures")

    if verify_package:
        item["package_verifier_passed"] = bool(package_results) and all(
            passed for passed, _included in package_results
        )
        item["package_with_assertion_report_verified"] = any(
            passed and included for passed, included in package_results
        )
        item["package_without_assertion_report_verified"] = any(
            passed and not included for passed, included in package_results
        )
    item["status"] = (
        "passed"
        if item["contract_valid"]
        and item["positive_examples_total"] > 0
        and item["positive_examples_passed"] == item["positive_examples_total"]
        and item["badcases_total"] > 0
        and item["badcases_passed"] == item["badcases_total"]
        and not item["unexpected_assertion_failures"]
        and (not verify_package or item["package_verifier_passed"] is True)
        else "failed"
    )
    return item


def evaluate_all(examples_root: Path, *, verify_package: bool) -> dict[str, Any]:
    items = [
        evaluate_pack(pack_dir, verify_package=verify_package)
        for pack_dir in sorted(
            path
            for path in examples_root.resolve().iterdir()
            if path.is_dir() and (path / "schema_pack.yaml").is_file()
        )
    ]
    passed = sum(item["status"] == "passed" for item in items)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if passed == len(items) and items else "failed",
        "total_schema_packs": len(items),
        "passed_schema_packs": passed,
        "failed_schema_packs": len(items) - passed,
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SchemaPack Contract Evaluation",
        "",
        f"- status: {report['status']}",
        f"- total SchemaPacks: {report['total_schema_packs']}",
        f"- passed SchemaPacks: {report['passed_schema_packs']}",
        f"- failed SchemaPacks: {report['failed_schema_packs']}",
        "",
        "| SchemaPack | Contract | Positive | Badcases | Package verifier | Status |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in report["items"]:
        lines.append(
            f"| {item['schema_pack_id']} | "
            f"{'passed' if item['contract_valid'] else 'failed'} | "
            f"{item['positive_examples_passed']}/{item['positive_examples_total']} | "
            f"{item['badcases_passed']}/{item['badcases_total']} | "
            f"{item['package_verifier_passed']} | {item['status']} |"
        )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--schema-pack", type=Path)
    group.add_argument("--all-examples", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--verify-package", action="store_true")
    args = parser.parse_args()

    if args.all_examples:
        report = evaluate_all(DEFAULT_EXAMPLES, verify_package=args.verify_package)
    else:
        item = evaluate_pack(args.schema_pack, verify_package=args.verify_package)
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": item["status"],
            "total_schema_packs": 1,
            "passed_schema_packs": int(item["status"] == "passed"),
            "failed_schema_packs": int(item["status"] != "passed"),
            "items": [item],
        }
    write_json(args.out, report)
    write_markdown(args.markdown, render_markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
