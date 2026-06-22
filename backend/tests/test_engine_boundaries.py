import hashlib

import pytest

from app.engines.chunk_engine import ChunkEngine
from app.engines.field_candidate_engine import FieldCandidateEngine
from app.engines.manifest_engine import generate_manifest
from app.schemas.canonical import CanonicalBlock, CanonicalModel
from app.schemas.uir import UIRBlock, UIRDocument


def _canonical(blocks: list[CanonicalBlock]) -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task_engine",
        doc_id="doc_engine",
        schema_id="schema_engine",
        blocks=blocks,
    )


def test_chunk_engine_rejects_invalid_size_and_handles_empty_document():
    engine = ChunkEngine()
    with pytest.raises(ValueError, match="greater than zero"):
        engine.chunk(_canonical([]), chunk_size=0)
    assert engine.chunk(_canonical([])).chunks == []


def test_chunk_engine_tracks_nested_headings_and_splits_oversized_text():
    canonical = _canonical(
        [
            CanonicalBlock(
                block_id="h1", type="heading", level=1, text="Main", source_blocks=["h1"]
            ),
            CanonicalBlock(
                block_id="p1", type="paragraph", text="alpha beta", source_blocks=["p1"]
            ),
            CanonicalBlock(
                block_id="h2", type="heading", level=2, text="Part", source_blocks=["h2"]
            ),
            CanonicalBlock(
                block_id="p2",
                type="paragraph",
                text="0123456789",
                source_blocks=["p2", "p2"],
            ),
        ]
    )

    chunks = ChunkEngine().chunk(canonical, chunk_size=6).chunks

    assert len(chunks) > 2
    assert [chunk.order for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].title_path == ["Main"]
    assert any(chunk.title_path == ["Main", "Part"] for chunk in chunks)
    assert all(len(chunk.text) <= 6 for chunk in chunks)
    assert all(len(chunk.source_blocks) == len(set(chunk.source_blocks)) for chunk in chunks)
    assert all(chunk.text_hash.startswith("sha256:") for chunk in chunks)


def test_chunk_fallback_metadata_is_stable_and_bounded():
    engine = ChunkEngine()
    assert engine._fallback_summary("") == ""
    assert len(engine._fallback_summary("x" * 300)) == 200
    assert engine._fallback_keywords("alpha alpha beta gamma delta epsilon zeta") == [
        "alpha",
        "beta",
        "gamma",
        "delta",
        "epsilon",
    ]


def test_candidate_engine_honors_include_flags_and_infers_types():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_candidates",
        metadata={"enabled": True, "count": 2, "ratio": 1.5, "date": "2026-06-22"},
        blocks=[
            UIRBlock(
                block_id="table_1",
                type="table",
                text="Status: active",
                attributes={"table_columns": ["name", 2]},
            )
        ],
    )
    engine = FieldCandidateEngine()

    metadata = engine.extract("task_candidates", uir, include_blocks=False)
    assert {candidate.inferred_type for candidate in metadata} == {
        "bool",
        "integer",
        "float",
        "date",
    }

    table = engine.extract("task_candidates", uir, include_metadata=False)
    assert {candidate.source_name for candidate in table} >= {"Status", "name", "2"}

    no_tables = engine.extract(
        "task_candidates",
        uir,
        include_metadata=False,
        include_tables=False,
    )
    assert not any(".table." in candidate.source_path for candidate in no_tables)


def test_candidate_engine_handles_invalid_columns_and_deduplicates():
    assert FieldCandidateEngine._table_columns({"columns": "not-a-list"}) == []
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_dedupe",
        blocks=[
            UIRBlock(
                block_id="h1",
                type="heading",
                level=1,
                text="Title",
                attributes={"name": "same"},
            )
        ],
    )
    engine = FieldCandidateEngine()
    candidates = engine.extract("task_dedupe", uir)
    assert len(candidates) == len({(c.source_path, str(c.value_sample)) for c in candidates})


def test_manifest_ignores_self_and_describes_unknown_assets(tmp_path):
    (tmp_path / "content.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("old", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    raw = b"custom-binary"
    (assets / "payload.unknownext").write_bytes(raw)

    manifest = generate_manifest("task_manifest", "doc_manifest", "pkg_manifest", tmp_path)
    by_path = {entry.path: entry for entry in manifest.files}

    assert list(by_path) == sorted(by_path)
    assert "manifest.json" not in by_path
    assert by_path["content.json"].required is True
    assert by_path["content.json"].role == "content"
    asset = by_path["assets/payload.unknownext"]
    assert asset.required is False
    assert asset.role == "asset"
    assert asset.media_type == "application/octet-stream"
    assert asset.sha256 == hashlib.sha256(raw).hexdigest()
