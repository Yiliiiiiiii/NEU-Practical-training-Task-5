"""Check Topic 5 correction alignment evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import create_app  # noqa: E402


REQUIRED_BOUNDARY_PHRASE = "SchemaPack 只是示例配置与评测基准，不是系统能力边界"
REQUIRED_INPUT_PHRASE = (
    "输入为 UIR + Target Schema + Metadata Template + Mapping Rules + "
    "Content Organization Config"
)
FORBIDDEN_PRODUCTION_CLAIM = "生产级盲测 0.85 已达成"


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def check() -> dict[str, Any]:
    openapi = create_app().openapi()
    paths = set(openapi.get("paths", {}))
    readme = _read_text(ROOT / "README.md")
    requirement_mapping = _read_text(ROOT / "docs" / "交接" / "requirement_mapping.md")
    docs_text = "\n".join(
        _read_text(path)
        for path in [
            ROOT / "README.md",
            ROOT / "docs" / "交接" / "requirement_mapping.md",
            ROOT / "docs" / "交接" / "acceptance_report.md",
            ROOT / "docs" / "交接" / "final_demo_script.md",
        ]
    )
    inline_report = _read_json(ROOT / "reports" / "topic5_inline_announcement_result.json")
    production_shadow = _read_json(ROOT / "reports" / "production_shadow_eval_report.json")
    false_claim_allowed = production_shadow.get("status") == "passed"

    checks = {
        "standard_convert_api": "/api/v1/topic5/convert" in paths,
        "schema_pack_contract": (ROOT / "schema_packs" / "README.md").is_file()
        and (ROOT / "schema_packs" / "schema_pack_contract.schema.json").is_file(),
        "no_code_schema_pack_demo": (
            ROOT / "schema_packs" / "examples" / "announcement_doc"
        ).is_dir(),
        "readme_positioning_corrected": REQUIRED_BOUNDARY_PHRASE in readme
        and REQUIRED_INPUT_PHRASE in readme,
        "requirement_mapping_corrected": REQUIRED_BOUNDARY_PHRASE in requirement_mapping
        and REQUIRED_INPUT_PHRASE in requirement_mapping,
        "announcement_inline_convert_passed": inline_report.get("status") == "passed"
        and inline_report.get("no_code_schema_pack_onboarding") is True,
        "no_false_production_blind_claim": false_claim_allowed
        or FORBIDDEN_PRODUCTION_CLAIM not in docs_text,
    }
    warnings: list[str] = []
    if not inline_report:
        warnings.append("topic5 inline conversion report is missing")
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "status": "passed" if not failed else "failed",
        "checks": checks,
        "failed_checks": failed,
        "warnings": warnings,
    }


def write_reports(report: dict[str, Any]) -> None:
    json_path = ROOT / "reports" / "topic5_alignment_gate_report.json"
    md_path = ROOT / "reports" / "topic5_alignment_gate_report.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Topic 5 Alignment Gate Report",
        "",
        f"- status: {report['status']}",
        f"- failed_checks: {', '.join(report['failed_checks']) or 'none'}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {name}: {'passed' if passed else 'failed'}"
        for name, passed in report["checks"].items()
    )
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = check()
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
