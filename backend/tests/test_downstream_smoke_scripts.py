import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = ROOT / "scripts" / "smoke_rag_ingest.py"
EXPORT_SCRIPT = ROOT / "scripts" / "export_training_corpus.py"


def load_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_rag_ingest_reads_directory_package(tmp_path):
    module = load_script(SMOKE_SCRIPT, "smoke_rag_ingest")
    package_dir = write_package(tmp_path)

    result = module.smoke_rag_ingest(package_dir, query="制度 管理")

    assert result["passed"] is True
    assert result["manifest_valid"] is True
    assert result["chunk_count"] == 1
    assert result["top_hit"]["chunk_id"] == "chunk_001"
    assert result["top_hit"]["source_linked"] is True


def test_smoke_rag_ingest_reads_zip_package(tmp_path):
    module = load_script(SMOKE_SCRIPT, "smoke_rag_ingest_zip")
    package_dir = write_package(tmp_path)
    zip_path = tmp_path / "package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package_dir.iterdir():
            archive.write(path, path.name)

    result = module.smoke_rag_ingest(zip_path, query="policy")

    assert result["passed"] is True
    assert result["top_hit"]["chunk_id"] == "chunk_001"


def test_smoke_rag_ingest_reports_missing_manifest(tmp_path):
    module = load_script(SMOKE_SCRIPT, "smoke_rag_ingest_missing_manifest")
    package_dir = write_package(tmp_path, include_manifest=False)

    result = module.smoke_rag_ingest(package_dir, query="policy")

    assert result["passed"] is False
    assert result["manifest_valid"] is False
    assert "manifest.json is missing" in result["errors"][0]


def test_smoke_rag_ingest_reports_empty_chunks(tmp_path):
    module = load_script(SMOKE_SCRIPT, "smoke_rag_ingest_empty_chunks")
    package_dir = write_package(tmp_path, chunks=[])

    result = module.smoke_rag_ingest(package_dir, query="policy")

    assert result["passed"] is False
    assert "does not contain any chunks" in result["errors"][0]


def test_smoke_rag_ingest_reports_invalid_jsonl(tmp_path):
    module = load_script(SMOKE_SCRIPT, "smoke_rag_ingest_invalid_jsonl")
    package_dir = write_package(tmp_path, chunks_text="{not valid json}\n")

    result = module.smoke_rag_ingest(package_dir, query="policy")

    assert result["passed"] is False
    assert "chunks.jsonl line 1 is invalid" in result["errors"][0]


def test_export_training_corpus_writes_jsonl_with_metadata(tmp_path):
    module = load_script(EXPORT_SCRIPT, "export_training_corpus")
    package_dir = write_package(tmp_path)
    output = tmp_path / "corpus" / "train.jsonl"

    result = module.export_training_corpus(package_dir, output)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert result["row_count"] == 1
    assert result["contract_id"] == "training_corpus_contract"
    assert result["contract_pass"] is True
    assert rows[0]["id"] == "chunk_001"
    assert rows[0]["text"].startswith("本制度")
    assert rows[0]["metadata"]["schema_id"] == "policy_doc"
    assert rows[0]["metadata"]["template_id"] == "policy_doc_base_v1"
    assert rows[0]["metadata"]["tags"]["content"] == ["policy", "scope"]
    assert rows[0]["metadata"]["source_block_ids"] == ["block_001"]


def test_export_training_corpus_supports_granularity_filter(tmp_path):
    module = load_script(EXPORT_SCRIPT, "export_training_corpus_granularity")
    package_dir = write_package(
        tmp_path,
        chunks=[
            {
                "chunk_id": "chunk_parent",
                "doc_id": "doc_001",
                "task_id": "task_001",
                "granularity": "parent",
                "text": "parent text",
                "summary": "parent",
                "keywords": [],
                "tags": {},
                "source_block_ids": ["block_001"],
            },
            {
                "chunk_id": "chunk_child",
                "doc_id": "doc_001",
                "task_id": "task_001",
                "granularity": "child",
                "parent_chunk_id": "chunk_parent",
                "text": "child text",
                "summary": "child",
                "keywords": [],
                "tags": {},
                "source_block_ids": ["block_001"],
            },
        ],
    )
    output = tmp_path / "corpus" / "child.jsonl"

    result = module.export_training_corpus(package_dir, output, granularity="child")
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert result["row_count"] == 1
    assert rows[0]["id"] == "chunk_child"
    assert rows[0]["metadata"]["granularity"] == "child"
    assert rows[0]["metadata"]["parent_chunk_id"] == "chunk_parent"


def write_package(
    tmp_path: Path,
    *,
    chunks: list[dict[str, Any]] | None = None,
    chunks_text: str | None = None,
    include_manifest: bool = True,
) -> Path:
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    (package_dir / "content.json").write_text('{"ok": true}\n', encoding="utf-8")
    (package_dir / "content.md").write_text("# Demo\n", encoding="utf-8")

    chunk_rows = [
        {
            "chunk_id": "chunk_001",
            "doc_id": "doc_001",
            "task_id": "task_001",
            "text": "本制度适用于管理部门 policy scope。",
            "summary": "本制度适用于管理部门。",
            "keywords": ["制度", "管理", "policy"],
            "tags": {
                "content": ["policy", "scope"],
                "management": ["schema:policy_doc", "template:policy_doc_base_v1"],
                "quality": ["source_linked"],
            },
            "source_block_ids": ["block_001"],
            "source_links": [{"block_id": "block_001", "source_path": "blocks[0]"}],
        }
    ]
    if chunks is not None:
        chunk_rows = chunks
    if chunks_text is None:
        chunks_text = "\n".join(json.dumps(row, ensure_ascii=False) for row in chunk_rows)
        if chunks_text:
            chunks_text += "\n"
    (package_dir / "chunks.jsonl").write_text(chunks_text, encoding="utf-8")

    if include_manifest:
        files = [
            manifest_file(package_dir, "content.json", "application/json", "structured_json"),
            manifest_file(package_dir, "content.md", "text/markdown", "markdown"),
            manifest_file(package_dir, "chunks.jsonl", "application/jsonl", "chunks"),
        ]
        manifest = {
            "manifest_version": "1.1",
            "package_id": "pkg_task_001",
            "package_version": "1.0.0",
            "task_id": "task_001",
            "doc_id": "doc_001",
            "created_at": "2026-06-26T00:00:00+00:00",
            "files": files,
            "generator": {
                "name": "SchemaPack Agent",
                "version": "test",
                "schema_id": "policy_doc",
                "schema_version": "1.0.0",
                "template_id": "policy_doc_base_v1",
            },
        }
        (package_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return package_dir


def manifest_file(
    package_dir: Path,
    relative_path: str,
    media_type: str,
    role: str,
) -> dict[str, Any]:
    path = package_dir / relative_path
    return {
        "path": relative_path,
        "required": True,
        "media_type": media_type,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "role": role,
    }
