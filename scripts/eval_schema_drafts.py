import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.draft_risk_service import DraftRiskService  # noqa: E402
from app.services.field_discovery_service import FieldDiscoveryService  # noqa: E402
from app.services.schema_draft_service import SchemaDraftService  # noqa: E402
from app.services.template_draft_service import TemplateDraftService  # noqa: E402


def load_documents(samples_dir: Path, limit: int) -> list[UIRDocument]:
    paths = sorted(samples_dir.glob("*.json"))[:limit]
    return [
        UIRDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Schema Draft Generator Evaluation", "", "## Summary", ""]
    for key, value in report.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def run(
    *,
    samples_dir: str | Path,
    out_path: str | Path,
    markdown_path: str | Path | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    documents = load_documents(Path(samples_dir), limit)
    if len(documents) < 5:
        raise ValueError("schema draft evaluation requires at least 5 samples")
    discovery = FieldDiscoveryService().discover(documents)
    schema = SchemaDraftService().generate(
        discovery,
        schema_id="evaluation_draft_doc",
        name="Evaluation Draft",
    )
    template = TemplateDraftService().generate(
        discovery,
        schema_id=schema.schema_id,
        template_id="evaluation_draft_doc_v1",
    )
    risk_report = DraftRiskService().scan(schema, template)
    evidence_backed = sum(
        1 for field in schema.fields if field.source_evidence and field.evidence_paths
    )
    payload_text = json.dumps(
        {
            "schema": schema.model_dump(mode="json"),
            "template": template.model_dump(mode="json"),
            "risk": risk_report.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )
    report = {
        "sample_count": len(documents),
        "candidate_count": len(discovery.field_candidates),
        "source_evidence_coverage": round(evidence_backed / len(schema.fields), 4),
        "risk_scan_ran": True,
        "risk_count": risk_report.risk_count,
        "must_not_auto_activate": (
            schema.must_not_auto_activate
            and template.must_not_auto_activate
            and risk_report.must_not_auto_activate
        ),
        "badcase_violations": risk_report.badcase_violations,
        "llm_auto_accepted_count": risk_report.llm_auto_accepted_count,
        "secret_leak_count": 1 if "sk-" in payload_text else 0,
    }
    write_json(Path(out_path), report)
    if markdown_path is not None:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Schema Draft Generator.")
    parser.add_argument("--samples", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown")
    parser.add_argument("--limit", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        samples_dir=args.samples,
        out_path=args.out,
        markdown_path=args.markdown,
        limit=args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
