"""Build a Phase C review evidence pack from generated SchemaPack packages."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGES_ROOT = ROOT / "reports" / "real_world_packages"
DEFAULT_JSON = ROOT / "reports" / "review_evidence_pack.json"
DEFAULT_MD = ROOT / "reports" / "review_evidence_pack.md"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _objects(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _review_id(doc_id: str, item: dict[str, Any]) -> str:
    source = item.get("source_field") if isinstance(item.get("source_field"), dict) else {}
    key = "|".join(
        str(part or "")
        for part in (
            doc_id,
            item.get("candidate_id"),
            item.get("target_field_id") or item.get("target_field"),
            source.get("source_path") or item.get("source_path"),
        )
    )
    return "rev_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _block_index(canonical: dict[str, Any]) -> dict[str, str]:
    blocks = canonical.get("blocks", [])
    index: dict[str, str] = {}
    if not isinstance(blocks, list):
        return index
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = block.get("block_id")
        text = block.get("text")
        if isinstance(block_id, str) and isinstance(text, str):
            index[block_id] = text
    return index


def _excerpt(item: dict[str, Any], blocks: dict[str, str], limit: int = 500) -> str:
    source_blocks = [value for value in item.get("source_blocks", []) if isinstance(value, str)]
    texts = [blocks[block_id] for block_id in source_blocks if block_id in blocks]
    if not texts:
        value = item.get("value_sample")
        texts = [value] if isinstance(value, str) else []
    excerpt = "\n".join(texts).strip()
    return excerpt[:limit]


def _suggestion(item: dict[str, Any]) -> tuple[str, str]:
    badcase = item.get("badcase_filter")
    if isinstance(badcase, dict) and badcase.get("blocked"):
        return "reject", "Badcase filter blocked this mapping candidate."
    flags = {flag for flag in item.get("risk_flags", []) if isinstance(flag, str)}
    if any(flag.startswith("forbidden_") for flag in flags):
        return "reject", "Risk flags include a forbidden semantic pair."
    return "keep_pending", "Review requires explicit human decision."


def build_pack(packages_root: str | Path) -> dict[str, Any]:
    root = Path(packages_root)
    reviews: list[dict[str, Any]] = []
    for package_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = package_dir / "manifest.json"
        mapping_path = package_dir / "mapping_report.json"
        canonical_path = package_dir / "canonical.json"
        if not manifest_path.exists() or not mapping_path.exists():
            continue
        manifest = _read_json(manifest_path)
        mapping = _read_json(mapping_path)
        canonical = _read_json(canonical_path) if canonical_path.exists() else {}
        blocks = _block_index(canonical)
        doc_id = str(manifest.get("doc_id") or mapping.get("doc_id") or package_dir.name)
        doc_type = str(mapping.get("schema_id") or manifest.get("generator", {}).get("schema_id") or "")
        for item in _objects(mapping.get("review_required_items")):
            source = item.get("source_field") if isinstance(item.get("source_field"), dict) else {}
            suggestion, reason = _suggestion(item)
            reviews.append(
                {
                    "review_id": _review_id(doc_id, item),
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "source_label": item.get("source_field_name")
                    or source.get("source_name")
                    or item.get("source_name"),
                    "source_value": item.get("value_sample"),
                    "target_field": item.get("target_field_id") or item.get("target_field"),
                    "confidence": item.get("confidence"),
                    "confidence_tier": item.get("confidence_tier"),
                    "risk_flags": item.get("risk_flags", []),
                    "badcase_filter": item.get("badcase_filter", {}),
                    "review_required_reason": item.get("review_required_reason"),
                    "source_path": source.get("source_path") or item.get("source_path"),
                    "source_blocks": item.get("source_blocks", []),
                    "source_excerpt": _excerpt(item, blocks),
                    "lineage_available": bool(item.get("source_blocks")),
                    "codex_suggestion": suggestion,
                    "codex_reason": reason,
                    "requires_human": True,
                }
            )
    suggestions = Counter(item["codex_suggestion"] for item in reviews)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "packages_root": str(root),
        "summary": {
            "review_count": len(reviews),
            "suggest_approve": suggestions.get("approve", 0),
            "suggest_reject": suggestions.get("reject", 0),
            "suggest_keep_pending": suggestions.get("keep_pending", 0),
            "requires_human": len(reviews),
        },
        "reviews": reviews,
    }


def render_markdown(pack: dict[str, Any]) -> str:
    lines = [
        "# Phase C Review Evidence Pack",
        "",
        f"- Generated at: {pack['generated_at']}",
        f"- Packages root: {pack['packages_root']}",
        f"- Review count: {pack['summary']['review_count']}",
        "",
        "| Review | Doc | Target | Source | Suggestion |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in pack["reviews"]:
        lines.append(
            "| "
            + " | ".join(
                str(value).replace("|", "\\|").replace("\n", " ")
                for value in (
                    item["review_id"],
                    item["doc_id"],
                    item["target_field"],
                    item["source_label"],
                    item["codex_suggestion"],
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def run(*, packages_root: str | Path, out_path: str | Path, markdown_path: str | Path) -> dict[str, Any]:
    pack = build_pack(packages_root)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(pack), encoding="utf-8")
    return pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-root", type=Path, default=DEFAULT_PACKAGES_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pack = run(
        packages_root=args.packages_root,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(pack["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
