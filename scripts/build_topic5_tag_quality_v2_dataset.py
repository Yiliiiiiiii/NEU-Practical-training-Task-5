"""Build the independently annotated, immutable Topic 5 tag-quality v2 set."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ANNOTATION_SPEC = ROOT / "eval" / "topic5_tag_quality" / "v2_annotation_spec.jsonl"
SOURCE_UIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_OUTPUT = ROOT / "eval" / "topic5_tag_quality" / "v2"
BASELINE_ENGINE_COMMIT = "70ff30236d90a3c9de0534a8f6313e5bb559cbf5"


CONTENT_DEFINITIONS = {
    "general": "General public-information or service-guide content.",
    "meeting": "Meeting minutes, agenda, or decision-record content.",
    "policy": "Policy, regulation, guidance, or normative-rule content.",
    "procurement": "Procurement notice, tender, or award content.",
}
QUALITY_DEFINITIONS = {
    "source_linked": "Every evaluated chunk declares canonical source block identifiers.",
    "anchor_linked": "Every evaluated chunk source link resolves to a canonical block anchor.",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
    )


def _uir_paths() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in sorted(SOURCE_UIR.glob("*/*.json")):
        if path.parent.name == "_rejected":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        result[str(payload["doc_id"])] = path
    return result


def _taxonomy(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    content = sorted({str(tag) for row in rows for tag in row["content_tags"]})
    management = sorted({str(tag) for row in rows for tag in row["management_tags"]})
    quality = sorted({str(tag) for row in rows for tag in row["quality_tags"]})
    return {
        "content": [
            {"tag": tag, "definition": CONTENT_DEFINITIONS[tag]} for tag in content
        ],
        "management": [
            {
                "tag": tag,
                "definition": (
                    f"Deterministic schema identity tag for {tag.removeprefix('schema:')}."
                    if tag.startswith("schema:")
                    else "Deterministic mapping/content template version identity tag."
                ),
            }
            for tag in management
        ],
        "quality": [
            {"tag": tag, "definition": QUALITY_DEFINITIONS[tag]} for tag in quality
        ],
    }


def _load_evaluator():
    path = ROOT / "scripts" / "eval_topic5_tag_quality_v2.py"
    spec = importlib.util.spec_from_file_location("_tag_v2_builder_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load tag v2 evaluator")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_manifest(
    output: Path,
    *,
    label_count: int,
    reference_count: int,
    annotation_source_sha256: str,
) -> None:
    files = {
        path.relative_to(output).as_posix(): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    dataset_sha = hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in files.items()).encode()
    ).hexdigest()
    payload_files = {
        name: digest for name, digest in files.items() if name != "baseline_report.json"
    }
    payload_sha = hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in payload_files.items()).encode()
    ).hexdigest()
    manifest_path = output / "manifest.json"
    dump_json(
        manifest_path,
        {
            "dataset_id": "topic5_tag_quality",
            "version": "2.0.0",
            "label_count": label_count,
            "source_reference_count": reference_count,
            "immutable": True,
            "dataset_sha256": dataset_sha,
            "payload_sha256": payload_sha,
            "annotation_source_path": ANNOTATION_SPEC.relative_to(ROOT).as_posix(),
            "annotation_source_sha256": annotation_source_sha256,
            "baseline_engine_commit": BASELINE_ENGINE_COMMIT,
            "files": files,
            "correction_policy": "create v3 with reason and before/after reports",
        },
    )
    (output.parent / f"{output.name}.manifest.sha256").write_text(
        _sha256(manifest_path) + "\n",
        encoding="utf-8",
    )


def build(output: Path, *, force: bool = False) -> None:
    seal_path = output.parent / f"{output.name}.manifest.sha256"
    if (output.exists() or seal_path.exists()) and not force:
        raise FileExistsError(
            f"output already exists; pass --force to overwrite: {output}"
        )
    if output.exists():
        shutil.rmtree(output)
    if seal_path.exists():
        seal_path.unlink()
    output.mkdir(parents=True)
    labels = load_jsonl(ANNOTATION_SPEC)
    annotation_source_sha = _sha256(ANNOTATION_SPEC)
    uir_paths = _uir_paths()
    references = []
    for row in labels:
        source_path = uir_paths[str(row["doc_id"])]
        references.append(
            {
                "doc_id": row["doc_id"],
                "source_path": source_path.relative_to(ROOT).as_posix(),
                "source_sha256": _sha256(source_path),
                "snapshot_scope": "referenced UIR plus frozen source hash",
            }
        )
    dump_jsonl(output / "labels.jsonl", labels)
    shutil.copyfile(ANNOTATION_SPEC, output / "annotation_spec.jsonl")
    dump_jsonl(output / "source_uir_refs.jsonl", references)
    dump_json(output / "taxonomy.json", _taxonomy(labels))
    card_lines = [
        "# Topic 5 Tag Quality v2",
        "",
        "## Annotation protocol and claim boundary",
        "",
        "An independent dataset annotator reads only the source-hashed UIR blocks named in",
        "the annotation specification, assigns content semantics, and records deterministic",
        "management/quality expectations with exact rule, trace, and chunk scope. Semantic",
        "anchor blocks were selected without projecting the earlier correlated gold groups.",
        "Reviewer role is `independent_dataset_annotator`; claims are limited to",
        "`public_fixture_baseline_only`. No production-blind claim is made.",
        "",
        "## Tag definitions",
        "",
        "Every tag and definition is machine-readable in `taxonomy.json`. Content tags are",
        "independent semantic labels scored with precision/recall/F1. Management and quality",
        "tags are deterministic contracts scored only for exact rule, trace, and scope.",
        "`schema:*` identifies the configured schema; `template_version:*` identifies its",
        "template version; `source_linked` requires source IDs; `anchor_linked` requires",
        "resolvable canonical anchors.",
        "",
        "## Immutability",
        "",
        "The manifest hashes every payload and baseline file; an external seal hashes the",
        "manifest itself. Corrections require v3, a reason, and before/after reports.",
        "",
    ]
    (output / "dataset_card.md").write_text(
        "\n".join(card_lines), encoding="utf-8"
    )
    # Provisional metadata lets the evaluator validate counts before the final hash freeze.
    payload_files = {
        path.relative_to(output).as_posix(): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    payload_sha = hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in payload_files.items()).encode()
    ).hexdigest()
    dump_json(
        output / "manifest.json",
        {
            "dataset_id": "topic5_tag_quality",
            "version": "2.0.0",
            "label_count": len(labels),
            "source_reference_count": len(references),
            "immutable": True,
            "dataset_sha256": payload_sha,
            "payload_sha256": payload_sha,
            "annotation_source_path": ANNOTATION_SPEC.relative_to(ROOT).as_posix(),
            "annotation_source_sha256": annotation_source_sha,
            "baseline_engine_commit": BASELINE_ENGINE_COMMIT,
            "files": payload_files,
            "correction_policy": "create v3 with reason and before/after reports",
        },
    )
    evaluator = _load_evaluator()
    report = evaluator.evaluate(output, verify_hashes=False)
    dump_json(output / "baseline_report.json", report)
    _write_manifest(
        output,
        label_count=len(labels),
        reference_count=len(references),
        annotation_source_sha256=annotation_source_sha,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        build(args.output.resolve(), force=args.force)
    except Exception as exc:
        import sys

        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
