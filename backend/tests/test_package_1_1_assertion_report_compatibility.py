from __future__ import annotations

import json
from pathlib import Path

from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.package_verifier_service import PackageVerifierService
from app.services.topic5_conversion_service import Topic5ConversionService

ROOT = Path(__file__).resolve().parents[2]
REQUEST_PATH = ROOT / "examples" / "topic5_inline" / "announcement_convert_request.json"


def package_request(*, include_assertion_report: bool) -> Topic5ConvertRequest:
    payload = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    payload.pop("output_assertions", None)
    if include_assertion_report:
        payload["output_assertions"] = {
            "contract_version": "1.0",
            "schema_id": "announcement_doc",
            "assertion_set_version": "1.0.0",
            "assertions": [
                {
                    "assertion_id": "title_non_empty",
                    "path": "$.data.title",
                    "operator": "non_empty",
                }
            ],
        }
        payload["options"]["include_assertion_report_in_package"] = True
    return Topic5ConvertRequest.model_validate(payload)


def test_package_1_1_without_assertion_report_still_passes(tmp_path) -> None:
    response = Topic5ConversionService(tmp_path).convert(
        package_request(include_assertion_report=False),
        create_package=True,
    )

    paths = {item["path"] for item in response.manifest["files"]}
    assert "reports/conversion_assertion_report.json" not in paths
    assert response.verifier_report["passed"] is True


def test_package_1_1_with_optional_assertion_report_passes(tmp_path) -> None:
    response = Topic5ConversionService(tmp_path).convert(
        package_request(include_assertion_report=True),
        create_package=True,
    )

    package_dir = Path(response.package_zip_path).parent
    assert (package_dir / "reports" / "conversion_assertion_report.json").is_file()
    assert PackageVerifierService().verify_package(package_dir).passed is True


def test_package_verifier_rejects_tampered_optional_assertion_report(tmp_path) -> None:
    response = Topic5ConversionService(tmp_path).convert(
        package_request(include_assertion_report=True),
        create_package=True,
    )
    package_dir = Path(response.package_zip_path).parent
    report_path = package_dir / "reports" / "conversion_assertion_report.json"
    report_path.write_text("{}", encoding="utf-8")

    verifier = PackageVerifierService().verify_package(package_dir)

    assert verifier.passed is False
    assert any(
        issue.path == "reports/conversion_assertion_report.json"
        and issue.code == "checksum_mismatch"
        for issue in verifier.errors
    )
