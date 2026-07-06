import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import build_lineage_demo_report  # noqa: E402

from tests.test_lineage_graph_service import build_graph  # noqa: E402


def test_builds_lineage_demo_report_from_graph(tmp_path: Path) -> None:
    graph_path = tmp_path / "lineage_graph.json"
    graph_path.write_text(
        json.dumps(build_graph().model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    out = tmp_path / "demo.json"
    markdown = tmp_path / "demo.md"

    report = build_lineage_demo_report.run(
        graph_path=graph_path,
        out_path=out,
        markdown_path=markdown,
    )

    assert report["task_id"] == "task_1"
    assert report["showcase"]["field"]["root"] == "title"
    assert report["showcase"]["chunk"]["root"] == "chunk_1"
    assert report["showcase"]["artifact"]["root"] == "chunks.jsonl"
    assert json.loads(out.read_text(encoding="utf-8"))["summary"]["node_count"] > 0
    assert "does not prove strict semantic correctness" in markdown.read_text(
        encoding="utf-8"
    )
