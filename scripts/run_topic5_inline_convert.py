"""Run the Topic 5 inline conversion demo request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.services.topic5_conversion_service import Topic5ConversionService  # noqa: E402


def run(
    request_path: Path,
    out_path: Path,
    *,
    create_package: bool = False,
    package_out: Path | None = None,
) -> dict[str, Any]:
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    request = Topic5ConvertRequest.model_validate(payload)
    storage_root = package_out or out_path.parent / "topic5_inline_announcement_package"
    response = Topic5ConversionService(storage_root).convert(
        request,
        create_package=create_package,
    )
    response_payload = response.model_dump(mode="json")
    passed = response.status == "completed" and (
        not create_package
        or bool(response.verifier_report and response.verifier_report.get("passed"))
    )
    report = {
        "status": "passed" if passed else "failed",
        "no_code_schema_pack_onboarding": bool(
            response.mapping_report["summary"].get("no_code_schema_pack_onboarding")
        ),
        "schema_id": response.schema_id,
        "template_id": response.template_id,
        "conversion_status": response.status,
        "package_verifier_passed": (
            response.verifier_report.get("passed")
            if response.verifier_report
            else None
        ),
        "response": response_payload,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--request",
        type=Path,
        default=ROOT / "examples" / "topic5_inline" / "announcement_convert_request.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "topic5_inline_announcement_result.json",
    )
    parser.add_argument("--create-package", action="store_true")
    parser.add_argument(
        "--package-out",
        type=Path,
        default=None,
        help="Storage root for generated package artifacts.",
    )
    args = parser.parse_args()
    report = run(
        args.request,
        args.out,
        create_package=args.create_package,
        package_out=args.package_out,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
