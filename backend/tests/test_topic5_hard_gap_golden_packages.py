from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.package_verifier_service import PackageVerifierService
from app.services.topic5_conversion_service import Topic5ConversionService

ROOT = Path(__file__).resolve().parents[2]


def _request(name: str) -> dict:
    path = ROOT / "examples" / "topic5_inline" / f"{name}_convert_request.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    source_block = payload["uir"]["blocks"][1]
    mention = (
        "Information Security School"
        if name == "event_notice"
        else source_block["text"].split("：", 1)[-1]
    )
    payload["uir"]["entities"] = [
        {
            "mention": mention,
            "canonical_name": mention,
            "entity_type": "organization",
            "normalized_id": f"org:{name}",
            "link_status": "linked",
            "confidence": 1.0,
            "source_block_ids": [source_block["block_id"]],
            "source_agent": "topic7",
            "evidence": {"fixture": "hard_gap_batch_1"},
        }
    ]
    return payload


@pytest.mark.parametrize(
    ("name", "expected_tag"),
    [("announcement", "announcement"), ("event_notice", "event_notice")],
)
def test_hard_gap_golden_package_covers_batch_features(
    tmp_path: Path, name: str, expected_tag: str
) -> None:
    request = Topic5ConvertRequest.model_validate(_request(name))

    result = Topic5ConversionService(tmp_path).convert(request, create_package=True)

    assert result.status == "completed"
    assert result.document_metadata
    assert result.document_summary and result.document_summary["faithfulness_passed"]
    assert result.artifact_consistency_report["passed"] is True
    assert result.artifact_consistency_report["block_coverage"] == 1.0
    assert result.artifact_consistency_report["chunk_source_coverage"] == 1.0
    assert all(expected_tag in chunk["content_tags"] for chunk in result.chunks)
    assert all(chunk["quality_tags"] for chunk in result.chunks)
    entity_chunks = [chunk for chunk in result.chunks if chunk["entity_tags"]]
    assert len(entity_chunks) == 1
    assert entity_chunks[0]["entity_tags"][0]["normalized_id"] == f"org:{name}"
    for block in request.uir.blocks:
        assert (
            f'<!-- topic5:block:start id="{block.block_id}"'
            in result.content_markdown
        )

    package_dir = Path(result.package_zip_path).parent
    metadata = json.loads((package_dir / "metadata.json").read_text(encoding="utf-8"))
    assert {
        "metadata_template_v1",
        "document_summary_v1",
        "artifact_consistency_v1",
    }.issubset(metadata["features"])
    manifest_paths = {item["path"] for item in result.manifest["files"]}
    assert {
        "artifact_consistency_report.json",
        "metadata_template_report.json",
        "verifier_report.json",
    }.issubset(manifest_paths)
    assert PackageVerifierService().verify_package(package_dir, strict=True).passed


@pytest.mark.parametrize("name", ["announcement", "event_notice"])
def test_hard_gap_semantic_artifacts_are_identical_across_three_runs(
    tmp_path: Path, name: str
) -> None:
    request_payload = _request(name)
    hashes = []
    for run in range(3):
        result = Topic5ConversionService(tmp_path / str(run)).convert(
            Topic5ConvertRequest.model_validate(copy.deepcopy(request_payload)),
            create_package=False,
        )
        actual_chunk_ids = {chunk["chunk_id"] for chunk in result.chunks}
        assert set(result.document_summary["source_chunk_ids"]) <= actual_chunk_ids
        hashes.append(_semantic_hashes(result))

    assert hashes[0] == hashes[1] == hashes[2]


def _semantic_hashes(result) -> dict[str, str]:
    task_id = result.task_id
    summary = _normalize_summary_identity(result.document_summary, task_id)
    content = {
        "data": result.content_json["data"],
        "document_metadata": result.content_json["document_metadata"],
        "document_summary": _normalize_summary_identity(
            result.content_json["document_summary"], task_id
        ),
        "blocks": result.content_json["blocks"],
    }
    chunks = []
    for chunk in result.chunks:
        semantic_chunk = {
            key: value
            for key, value in chunk.items()
            if key not in {"task_id"}
        }
        chunks.append(_normalize_chunk_identity(semantic_chunk, task_id))
    return {
        "content_semantic_hash": _hash(content),
        "document_metadata_hash": _hash(result.document_metadata),
        "summary_hash": _hash(summary),
        "chunk_semantic_hashes": _hash(chunks),
        "tag_traces": _hash(
            [chunk["organization_trace"]["tag_traces"] for chunk in result.chunks]
        ),
        "entity_tags": _hash([chunk["entity_tags"] for chunk in result.chunks]),
        "consistency_checks": _hash(result.artifact_consistency_report["checks"]),
    }


def test_run_identity_normalization_does_not_rewrite_business_text() -> None:
    task_id = "topic5_run_a"
    value = {"title": f"customer {task_id}", "chunk_id": f"chunk_{task_id}_0001"}

    normalized = _normalize_chunk_identity(value, task_id)

    assert normalized["title"] == f"customer {task_id}"
    assert normalized["chunk_id"] == "chunk_<task_id>_0001"


def test_content_semantic_hash_uses_the_content_artifact_summary() -> None:
    def result_with_content_summary(text: str) -> SimpleNamespace:
        summary = {"text": "top-level", "source_chunk_ids": []}
        return SimpleNamespace(
            task_id="topic5_run_a",
            content_json={
                "data": {},
                "document_metadata": {},
                "document_summary": {"text": text, "source_chunk_ids": []},
                "blocks": [],
            },
            document_metadata={},
            document_summary=summary,
            chunks=[],
            artifact_consistency_report={"checks": []},
        )

    first = _semantic_hashes(result_with_content_summary("content-a"))
    second = _semantic_hashes(result_with_content_summary("content-b"))

    assert first["content_semantic_hash"] != second["content_semantic_hash"]
    assert first["summary_hash"] == second["summary_hash"]


def _normalize_summary_identity(summary: dict, task_id: str) -> dict:
    normalized = copy.deepcopy(summary)
    normalized["source_chunk_ids"] = [
        _normalize_chunk_reference(chunk_id, task_id)
        for chunk_id in summary["source_chunk_ids"]
    ]
    return normalized


def _normalize_chunk_identity(chunk: dict, task_id: str) -> dict:
    normalized = copy.deepcopy(chunk)
    normalized["chunk_id"] = _normalize_chunk_reference(chunk["chunk_id"], task_id)
    if chunk.get("parent_chunk_id"):
        normalized["parent_chunk_id"] = _normalize_chunk_reference(
            chunk["parent_chunk_id"], task_id
        )
    return normalized


def _normalize_chunk_reference(chunk_id: str, task_id: str) -> str:
    prefix = f"chunk_{task_id}_"
    if chunk_id.startswith(prefix):
        return f"chunk_<task_id>_{chunk_id.removeprefix(prefix)}"
    return chunk_id


def _hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
