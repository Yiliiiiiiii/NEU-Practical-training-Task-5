import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_evaluation_center_scorecard.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_evaluation_center_scorecard",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builds_scorecard_json_and_markdown(tmp_path: Path) -> None:
    module = load_module()
    metrics_path = tmp_path / "metrics.json"
    gates_path = tmp_path / "gates.json"
    out_path = tmp_path / "scorecard.json"
    markdown_path = tmp_path / "scorecard.md"
    metrics_path.write_text(
        json.dumps(
            {
                "package_verification_rate": 1.0,
                "strict_validation_rate": 17 / 35,
                "badcase_violation_count": 0,
                "llm_auto_accepted_count": 0,
                "adapter_trace_coverage": 1.0,
            }
        ),
        encoding="utf-8",
    )
    gates_path.write_text(
        json.dumps(
            {
                "gates": [
                    {
                        "metric": "badcase_violation_count",
                        "op": "==",
                        "value": 0,
                    },
                    {
                        "metric": "package_verification_rate",
                        "op": ">=",
                        "value": 1.0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = module.run(
        metrics_path=metrics_path,
        gates_path=gates_path,
        out_path=out_path,
        markdown_path=markdown_path,
    )

    assert report["summary"]["status"] == "passed"
    assert report["summary"]["gates_passed"] == 2
    cards = {item["metric_id"]: item for item in report["cards"]}
    assert cards["strict_validation_rate"]["status"] == "needs_attention"
    assert cards["badcase_violation_count"]["status"] == "passed"
    assert json.loads(out_path.read_text(encoding="utf-8")) == report
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## Metrics" in markdown
    assert "## Regression Gates" in markdown
    assert "## Known Gaps" in markdown
    assert "## Reproduction" in markdown
