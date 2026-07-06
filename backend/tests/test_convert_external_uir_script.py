import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "convert_external_uir.py"
FIXTURE = (
    ROOT
    / "examples"
    / "external_uir"
    / "dialect_a_block_list"
    / "sample_procurement_external.json"
)


def load_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("convert_external_uir", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_convert_external_uir_writes_standard_uir_report_and_route(tmp_path) -> None:
    module = load_module()
    out = tmp_path / "standard_uir.json"
    report = tmp_path / "adapter_report.json"
    route_report = tmp_path / "route_report.json"

    result = module.run(
        input_path=FIXTURE,
        source_system="topic11",
        out_path=out,
        report_path=report,
        route_schema=True,
        route_report_path=route_report,
    )

    assert result["doc_id"] == "ext_proc_001"
    assert out.is_file()
    assert report.is_file()
    assert route_report.is_file()
    assert json.loads(out.read_text(encoding="utf-8"))["doc_id"] == "ext_proc_001"
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "passed"
    route = json.loads(route_report.read_text(encoding="utf-8"))
    assert route["selected_schema_id"] == "procurement_doc"
    assert route["selected_template_id"] == "procurement_doc_base_v1"
