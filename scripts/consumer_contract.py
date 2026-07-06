"""Versioned downstream consumer contract verification."""

import csv
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from export_rag_corpus import export_rag_corpus  # noqa: E402
from export_structured_csv import export_structured_csv  # noqa: E402
from export_training_corpus import export_training_corpus  # noqa: E402
from package_consumption import (  # noqa: E402
    PackageReadError,
    load_manifest,
    resolved_package_dir,
    validate_manifest_files,
)


def load_contract(contract_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("consumer contract must be a JSON object")
    for key in ("contract_id", "version", "artifact_type"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ValueError(f"consumer contract is missing {key}")
    if payload["artifact_type"] not in {"csv", "jsonl", "package"}:
        raise ValueError("unsupported consumer contract artifact_type")
    return payload


def verify_consumer_contract(
    package_path: str | Path,
    contract_path: str | Path,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    package = Path(package_path)
    errors: list[str] = []
    record_count = 0
    output_format = str(contract["artifact_type"])
    try:
        if output_format == "package":
            records = [_package_record(package, contract)]
        else:
            records = _export_records(package, contract)
        record_count = len(records)
        if not records:
            errors.append("consumer export contains no records")
        errors.extend(_required_field_errors(records, contract))
    except (OSError, ValueError, PackageReadError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    return {
        "contract_id": contract["contract_id"],
        "contract_version": contract["version"],
        "artifact_type": output_format,
        "input_package": str(package),
        "record_count": record_count,
        "passed": not errors,
        "contract_pass": not errors,
        "errors": errors,
    }


def verify_batch(
    package_root: str | Path,
    contract_path: str | Path,
) -> dict[str, Any]:
    root = Path(package_root)
    packages = [root] if root.is_file() else sorted(root.rglob("*.zip"))
    items = [
        verify_consumer_contract(package, contract_path)
        for package in packages
    ]
    passed_count = sum(1 for item in items if item["passed"])
    package_count = len(items)
    return {
        "contract_id": load_contract(contract_path)["contract_id"],
        "package_count": package_count,
        "passed_count": passed_count,
        "failed_count": package_count - passed_count,
        "consumer_contract_pass_rate": round(
            passed_count / package_count,
            4,
        )
        if package_count
        else 0.0,
        "items": items,
    }


def write_report(
    report: dict[str, Any],
    *,
    json_path: str | Path,
    markdown_path: str | Path | None = None,
) -> None:
    output = Path(json_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if markdown_path is not None:
        markdown = Path(markdown_path)
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(report), encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Consumer Contract Report", ""]
    for key in (
        "contract_id",
        "package_count",
        "passed_count",
        "failed_count",
        "consumer_contract_pass_rate",
    ):
        if key in report:
            lines.append(f"- {key}: {report[key]}")
    if "input_package" in report:
        lines.extend(
            [
                f"- input_package: {report['input_package']}",
                f"- passed: {report['passed']}",
                f"- record_count: {report['record_count']}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _package_record(
    package_path: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    with resolved_package_dir(package_path) as package_dir:
        manifest = load_manifest(package_dir)
        validate_manifest_files(package_dir, manifest)
        missing = [
            name
            for name in contract.get("required_package_files", [])
            if not (package_dir / name).is_file()
        ]
        if missing:
            raise PackageReadError(
                "required package files missing: " + ", ".join(missing)
            )
        return {"manifest": manifest}


def _export_records(
    package_path: Path,
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    exporter = contract.get("exporter")
    with TemporaryDirectory(prefix="consumer-contract-") as raw:
        temp = Path(raw)
        if exporter == "export_rag_corpus":
            output = temp / "rag.jsonl"
            export_rag_corpus(package_path, output)
            return _read_jsonl(output)
        if exporter == "export_training_corpus":
            output = temp / "training.jsonl"
            export_training_corpus(package_path, output)
            return _read_jsonl(output)
        if exporter == "export_structured_csv":
            output = temp / "structured.csv"
            export_structured_csv(package_path, output)
            with output.open(encoding="utf-8-sig", newline="") as file:
                return list(csv.DictReader(file))
    raise ValueError(f"unsupported consumer contract exporter: {exporter}")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"export line {line_number} must be a JSON object")
        rows.append(value)
    return rows


def _required_field_errors(
    records: list[dict[str, Any]],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        for field_path in contract.get("required_fields", []):
            if not _has_path(record, str(field_path)):
                errors.append(
                    f"record {index} missing required field {field_path}"
                )
    return errors


def _has_path(record: dict[str, Any], field_path: str) -> bool:
    value: Any = record
    for part in field_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return value is not None
