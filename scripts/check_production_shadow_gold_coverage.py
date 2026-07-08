"""Check production shadow manifest and gold-label coverage."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BLOCKER_REASON = (
    "Cannot claim 0.85 because independent production blind UIR corpus "
    "with gold labels is missing."
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must contain an object")
            rows.append(value)
    return rows


def _blocked_report(manifest: Path, gold: Path) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "blocked",
        "can_claim_0_85": False,
        "reason": BLOCKER_REASON,
        "manifest": str(manifest),
        "gold": str(gold),
        "blind_doc_count": 0,
        "gold_label_count": 0,
        "errors": [
            f"Missing manifest: {manifest}" if not manifest.exists() else "",
            f"Missing gold: {gold}" if not gold.exists() else "",
        ],
    }


def build_report(manifest_path: Path, gold_path: Path) -> dict[str, Any]:
    if not manifest_path.exists() or not gold_path.exists():
        report = _blocked_report(manifest_path, gold_path)
        report["errors"] = [error for error in report["errors"] if error]
        return report
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    documents = manifest.get("documents", manifest.get("docs", []))
    if not isinstance(documents, list):
        documents = []
    blind_docs = [
        doc for doc in documents if isinstance(doc, dict) and doc.get("split") == "blind"
    ]
    gold_rows = _load_jsonl(gold_path)
    gold_by_doc: dict[str, list[dict[str, Any]]] = {}
    for row in gold_rows:
        doc_id = row.get("doc_id")
        if isinstance(doc_id, str):
            gold_by_doc.setdefault(doc_id, []).append(row)

    errors: list[str] = []
    for doc in blind_docs:
        doc_id = str(doc.get("doc_id") or "")
        rows = gold_by_doc.get(doc_id, [])
        required_rows = [row for row in rows if row.get("required") is True]
        if not required_rows:
            errors.append(f"blind doc missing required gold: {doc_id}")
        for row in required_rows:
            if not row.get("source_block_ids") and not row.get("source_quote"):
                errors.append(f"required gold lacks source evidence: {doc_id}")
        if doc.get("doc_type") == "policy_doc":
            fields = {row.get("target_field") for row in rows}
            if not ({"publish_date", "issuer"} & fields):
                errors.append(f"policy blind doc lacks date/issuer gold: {doc_id}")

    if not blind_docs:
        errors.append("production shadow manifest has no blind docs")
    if not gold_rows:
        errors.append("production shadow gold labels are empty")
    status = "passed" if blind_docs and gold_rows and not errors else "blocked"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "can_claim_0_85": status == "passed",
        "dataset_id": manifest.get("dataset_id"),
        "manifest": str(manifest_path),
        "gold": str(gold_path),
        "blind_doc_count": len(blind_docs),
        "gold_label_count": len(gold_rows),
        "errors": errors,
        "reason": None if status == "passed" else BLOCKER_REASON,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Production Shadow Gold Coverage",
        "",
        f"- Status: {report['status']}",
        f"- Blind docs: {report['blind_doc_count']}",
        f"- Gold labels: {report['gold_label_count']}",
        f"- Can claim 0.85: {report['can_claim_0_85']}",
    ]
    if report.get("reason"):
        lines.extend(["", str(report["reason"])])
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def write_reports(
    report: dict[str, Any],
    out: Path,
    markdown: Path,
    blocker_markdown: Path | None,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(report)
    markdown.write_text(rendered, encoding="utf-8")
    if report["status"] == "blocked" and blocker_markdown is not None:
        blocker_markdown.parent.mkdir(parents=True, exist_ok=True)
        blocker_markdown.write_text(
            "# Production Shadow Dataset Blocker\n\n" + BLOCKER_REASON + "\n",
            encoding="utf-8",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument(
        "--blocker-markdown",
        type=Path,
        default=ROOT / "reports" / "production_shadow_dataset_blocker_report.md",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args.manifest, args.gold)
    write_reports(report, args.out, args.markdown, args.blocker_markdown)
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    if report["status"] == "blocked":
        return 2
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
