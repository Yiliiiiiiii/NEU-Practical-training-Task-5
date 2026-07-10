import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = ROOT / "scripts" / "export_openapi.py"


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_openapi", EXPORT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openapi_export_includes_demo_workflow_paths(tmp_path):
    module = load_export_module()

    output = tmp_path / "openapi.json"
    schema = module.export_openapi(output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert written == schema
    for path in [
        "/api/v1/documents/import",
        "/api/v1/schemas",
        "/api/v1/templates",
        "/api/v1/tasks",
        "/api/v1/tasks/{task_id}/execute",
        "/api/v1/tasks/{task_id}/reports/{report_name}",
        "/api/v1/tasks/{task_id}/package/download",
    ]:
        assert path in schema["paths"]


def test_openapi_check_detects_drift_without_rewriting_expected_file(tmp_path):
    module = load_export_module()
    expected = tmp_path / "openapi.json"
    module.export_openapi(expected)
    original = expected.read_bytes()

    assert module.check_openapi_drift(expected) is True
    assert expected.read_bytes() == original

    expected.write_text("{}\n", encoding="utf-8")
    drifted = expected.read_bytes()
    assert module.check_openapi_drift(expected) is False
    assert expected.read_bytes() == drifted
