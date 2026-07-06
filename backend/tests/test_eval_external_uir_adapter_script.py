import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_external_uir_adapter.py"
FIXTURES = ROOT / "examples" / "external_uir"


def load_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("eval_external_uir_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_eval_external_uir_adapter_writes_json_and_markdown(tmp_path) -> None:
    module = load_module()
    out = tmp_path / "eval_report.json"
    markdown = tmp_path / "eval_report.md"

    report = module.run(fixtures_dir=FIXTURES, out_path=out, markdown_path=markdown)

    assert report["adapter_fixture_count"] == 18
    assert report["adapter_selection_accuracy"] == 1.0
    assert report["uir_validation_pass_count"] == 18
    assert report["trace_coverage"] >= 0.95
    assert report["router_top1_accuracy"] >= 0.85
    assert report["router_review_required_count"] >= 1
    assert report["llm_auto_accepted_count"] == 0
    assert report["badcase_violations"] == 0
    assert report["secret_leaks"] == 0
    assert json.loads(out.read_text(encoding="utf-8"))["adapter_fixture_count"] == 18
    text = markdown.read_text(encoding="utf-8")
    assert "## Summary" in text
    assert "router_top1_accuracy" in text
