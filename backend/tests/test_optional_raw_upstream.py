import sys
from pathlib import Path

import fitz
import pytest
from test_downstream_exports import load_script

from app.adapters.base import AdapterInput
from app.adapters.registry import build_default_registry


def write_pdf(path: Path, *, text: str | None) -> Path:
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text, fontsize=16)
        page.insert_text(
            (72, 110),
            "This policy defines procurement review and supplier controls.",
            fontsize=11,
        )
    document.save(path)
    document.close()
    return path


def missing_provider(_: Path):
    raise ModuleNotFoundError("optional provider is not installed")


def test_docling_fallback_produces_adapter_compatible_external_uir(
    tmp_path: Path,
) -> None:
    module = load_script("upstream_external_uir")
    source = write_pdf(tmp_path / "sample.pdf", text="Sample Procurement Policy")

    result = module.convert_raw_document(
        source,
        provider="docling",
        provider_runner=missing_provider,
    )

    external = result["external_uir"]
    report = result["report"]
    assert external["title"] == "Sample Procurement Policy"
    assert external["chunks"]
    assert report["provider_requested"] == "docling"
    assert report["provider_used"] == "pymupdf_text"
    assert report["fallback_used"] is True
    assert report["auto_imported"] is False
    assert report["llm_auto_accepted_count"] == 0
    assert "api_key" not in str(report).lower()

    converted = build_default_registry().convert(
        AdapterInput(payload=external, source_system="raw_upstream")
    )
    assert converted.adapter_report.adapter_id == "block_list"
    assert converted.standard_uir.blocks


def test_scanned_pdf_is_rejected_without_ocr(tmp_path: Path) -> None:
    module = load_script("upstream_external_uir")
    source = write_pdf(tmp_path / "scan.pdf", text=None)

    with pytest.raises(ValueError, match="unsupported_scanned_pdf"):
        module.convert_raw_document(
            source,
            provider="unstructured",
            provider_runner=missing_provider,
        )


def test_importing_provider_wrappers_needs_no_optional_dependency() -> None:
    before = set(sys.modules)
    load_script("upstream_docling_to_external_uir")
    load_script("upstream_unstructured_to_external_uir")

    added = set(sys.modules) - before
    assert not any(name == "docling" or name.startswith("docling.") for name in added)
    assert not any(
        name == "unstructured" or name.startswith("unstructured.")
        for name in added
    )
