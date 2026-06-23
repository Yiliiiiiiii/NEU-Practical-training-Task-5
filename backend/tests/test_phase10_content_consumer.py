import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from app.engines.chunk_engine import ChunkEngine
from app.renderers.json_renderer import JSONRenderer
from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel


def _field(value, typ: str = "string") -> CanonicalField:
    return CanonicalField(value=value, type=typ)


def test_content_metadata_includes_labels_and_upstream_entities():
    canonical = CanonicalModel(
        canonical_version="1.0",
        task_id="task_content_labels",
        doc_id="doc_content_labels",
        schema_id="schema_content_labels",
        doc_meta={"source_name": "policy.json"},
        fields={
            "title": _field("城市更新政策"),
            "summary": _field("面向城市更新项目的审批政策。"),
            "keywords": _field(["城市更新", "审批"]),
            "publish_org": _field("市发展改革委"),
            "doc_type": _field("policy"),
        },
        blocks=[
            CanonicalBlock(
                block_id="blk_1",
                type="heading",
                level=1,
                text="城市更新政策",
                source_blocks=["blk_1"],
            )
        ],
    )

    content = JSONRenderer().render(canonical)

    assert content.metadata.document_summary == "面向城市更新项目的审批政策。"
    assert content.metadata.keywords == ["城市更新", "审批"]
    assert "policy" in content.metadata.content_tags
    assert "publish_org:市发展改革委" in content.metadata.upstream_entities
    assert content.metadata.management_tags
    assert content.metadata.quality_tags


def test_chunk_engine_populates_summary_keywords_and_three_label_tiers():
    canonical = CanonicalModel(
        canonical_version="1.0",
        task_id="task_chunks_labels",
        doc_id="doc_chunks_labels",
        schema_id="schema_chunks_labels",
        blocks=[
            CanonicalBlock(
                block_id="blk_h",
                type="heading",
                level=1,
                text="Policy Notice",
                source_blocks=["blk_h"],
            ),
            CanonicalBlock(
                block_id="blk_p",
                type="paragraph",
                text="The finance office approves this policy notice for project records.",
                source_blocks=["blk_p"],
            ),
        ],
    )

    [chunk] = ChunkEngine().chunk(canonical, chunk_size=500).chunks

    assert chunk.summary.startswith("Policy Notice")
    assert "Policy" in chunk.keywords
    assert chunk.labels.content_tags
    assert chunk.labels.management_tags
    assert chunk.labels.quality_tags


def test_consume_package_cli_reads_business_data_and_chunk_links(tmp_path):
    content = {
        "content_version": "1.1",
        "doc_id": "doc_consumer",
        "task_id": "task_consumer",
        "schema_ref": {"schema_id": "schema_consumer", "version": "1.0.0"},
        "metadata": {"keywords": ["alpha"]},
        "data": {"title": "Consumer Test"},
        "blocks": [
            {
                "block_id": "blk_1",
                "type": "paragraph",
                "text": "Consumer Test",
                "source_blocks": ["blk_1"],
            }
        ],
        "assets": [],
    }
    chunks = {
        "chunks_version": "1.0",
        "doc_id": "doc_consumer",
        "task_id": "task_consumer",
        "chunks": [
            {
                "chunk_id": "chk_task_consumer_0",
                "order": 0,
                "text": "Consumer Test",
                "source_blocks": ["blk_1"],
                "title_path": [],
                "labels": {
                    "content_tags": ["general"],
                    "management_tags": ["body"],
                    "quality_tags": ["linked"],
                },
                "summary": "Consumer Test",
                "keywords": ["Consumer"],
                "text_hash": "sha256:test",
            }
        ],
    }
    payloads = {
        "content.json": json.dumps(content).encode("utf-8"),
        "chunks.json": json.dumps(chunks).encode("utf-8"),
    }
    manifest = {
        "manifest_version": "1.0",
        "package_id": "pkg_consumer",
        "package_version": "10.0.0-test",
        "task_id": "task_consumer",
        "doc_id": "doc_consumer",
        "created_at": "2026-06-23T00:00:00+00:00",
        "files": [
            {
                "path": path,
                "required": True,
                "media_type": "application/json",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "role": path.rsplit(".", 1)[0],
            }
            for path, raw in sorted(payloads.items())
        ],
        "generator": {"name": "test", "version": "10"},
    }
    zip_path = tmp_path / "package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, raw in payloads.items():
            archive.writestr(path, raw)
        archive.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))

    result = subprocess.run(
        [sys.executable, "-m", "app.tools.consume_package", str(zip_path)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    body = json.loads(result.stdout)
    assert body == {
        "doc_id": "doc_consumer",
        "task_id": "task_consumer",
        "content_field_count": 1,
        "chunk_count": 1,
        "source_block_coverage": 1.0,
    }
