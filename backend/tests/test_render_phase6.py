import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.engines.transform_engine import TransformEngine
from app.renderers.chunks_renderer import ChunksRenderer
from app.renderers.json_renderer import JSONRenderer
from app.renderers.markdown_renderer import MarkdownRenderer
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.canonical_service import CanonicalService
from app.services.render_service import RenderService
from app.services.storage_service import StorageService

EXAMPLES = Path(__file__).resolve().parent.parent.parent / "examples" / "demo"


def _load_json(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    with TestSession() as session:
        yield session


@pytest.fixture()
def storage(tmp_path):
    return StorageService(tmp_path / "storage")


def _seed_full_pipeline(db_session, storage, doc_name, schema_name, template_name):
    uir_data = _load_json(doc_name)
    doc_id = uir_data["doc_id"]
    schema_data = _load_json(schema_name)
    schema_id = schema_data["schema_id"]
    template_data = _load_json(template_name)
    template_id = template_data["template_id"]

    storage.save_json(f"documents/{doc_id}/uir.json", uir_data)

    doc = Document(
        doc_id=doc_id,
        title=uir_data["metadata"].get("文档标题") or uir_data["metadata"].get("政策名称", ""),
        uir_version=uir_data["uir_version"],
        storage_path=f"documents/{doc_id}/uir.json",
        block_count=len(uir_data.get("blocks", [])),
    )
    db_session.add(doc)

    schema = TargetSchemaRecord(
        schema_id=schema_id,
        name=schema_data["name"],
        version=schema_data["version"],
        schema_json=json.dumps(schema_data, ensure_ascii=False),
        json_schema=json.dumps(schema_data.get("json_schema", {}), ensure_ascii=False),
    )
    db_session.add(schema)

    template = MappingTemplateRecord(
        template_id=template_id,
        schema_id=schema_id,
        name=template_data["name"],
        version=template_data["version"],
        template_json=json.dumps(template_data, ensure_ascii=False),
    )
    db_session.add(template)

    task_id = f"task_{doc_id}"
    task = ConversionTask(
        task_id=task_id,
        doc_id=doc_id,
        schema_id=schema_id,
        schema_version=schema_data["version"],
        template_id=template_id,
        template_version=template_data["version"],
        status="mapping_completed",
        input_hash="sha256:test",
    )
    db_session.add(task)

    engine = TransformEngine()
    uir = UIRDocument.model_validate(uir_data)
    candidates = engine._resolve_source = lambda uir, path: None
    from app.engines.field_candidate_engine import FieldCandidateEngine
    cand_engine = FieldCandidateEngine()
    candidates = cand_engine.extract(task_id=task_id, uir=uir)

    for cand in candidates:
        db_session.add(FieldCandidateRecord(
            candidate_id=cand.candidate_id,
            task_id=cand.task_id,
            doc_id=cand.doc_id,
            source_path=cand.source_path,
            source_name=cand.source_name,
            display_name=cand.display_name,
            value_sample=(
                json.dumps(cand.value_sample, ensure_ascii=False)
                if cand.value_sample is not None else None
            ),
            inferred_type=cand.inferred_type,
            source_blocks_json=json.dumps(cand.source_blocks, ensure_ascii=False),
            confidence=cand.confidence,
        ))

    from app.engines.mapping_engine import MappingEngine
    mapping_engine = MappingEngine()
    target_schema = TargetSchema.model_validate(schema_data)
    from app.schemas.mapping_template import MappingTemplate
    template_obj = MappingTemplate.model_validate(template_data)
    mappings = mapping_engine.map_fields(
        task_id=task_id,
        candidates=candidates,
        target_schema=target_schema,
        template=template_obj,
        review_threshold=0.8,
    )

    for m in mappings:
        db_session.add(FieldMappingRecord(
            mapping_id=m.mapping_id,
            task_id=m.task_id,
            candidate_id=m.candidate_id,
            target_field_id=m.target_field_id,
            method=m.method,
            confidence=m.confidence,
            status=m.status,
            need_review=m.need_review,
            evidence_json=json.dumps(m.evidence, ensure_ascii=False),
        ))

    db_session.commit()

    canonical_svc = CanonicalService(db_session, storage)
    canonical = canonical_svc.build_canonical(task_id, target_schema, template_obj)

    return task_id, canonical, target_schema, template_obj


# ─── 1. General demo real chain: three outputs ───


def test_general_demo_real_chain_three_outputs(db_session, storage):
    """General demo through full pipeline produces content.json, content.md, chunks.json."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    render_svc = RenderService(db_session, storage)
    outputs = render_svc.render_all(task_id)

    assert "content.json" in outputs
    assert "content.md" in outputs
    assert "chunks.json" in outputs

    cj = json.loads((storage.root / f"tasks/{task_id}/content.json").read_text(encoding="utf-8"))
    assert cj["content_version"] == "1.1"
    assert cj["doc_id"] == canonical.doc_id
    assert cj["task_id"] == task_id
    assert "title" in cj["data"] or "summary" in cj["data"]
    assert len(cj["blocks"]) > 0

    cm = (storage.root / f"tasks/{task_id}/content.md").read_text(encoding="utf-8")
    assert "---" in cm
    assert "doc_id:" in cm
    assert "block_id:" in cm

    ck = json.loads((storage.root / f"tasks/{task_id}/chunks.json").read_text(encoding="utf-8"))
    assert ck["chunks_version"] == "1.0"
    assert len(ck["chunks"]) > 0
    for chunk in ck["chunks"]:
        assert "chunk_id" in chunk
        assert "source_blocks" in chunk


# ─── 2. Policy demo real chain: date, enum, merge, assets ───


def test_policy_demo_real_chain(db_session, storage):
    """Policy demo produces valid outputs with date, enum, merge fields."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_policy_doc.json",
        "target_schema_policy.json",
        "mapping_template_policy.json",
    )

    render_svc = RenderService(db_session, storage)
    outputs = render_svc.render_all(task_id)
    assert len(outputs) == 3

    cj = json.loads((storage.root / f"tasks/{task_id}/content.json").read_text(encoding="utf-8"))
    assert "title" in cj["data"] or "publish_org" in cj["data"]

    cm = (storage.root / f"tasks/{task_id}/content.md").read_text(encoding="utf-8")
    assert "block_id:" in cm

    ck = json.loads((storage.root / f"tasks/{task_id}/chunks.json").read_text(encoding="utf-8"))
    assert len(ck["chunks"]) >= 1


# ─── 3. content.json data comes from canonical fields ───


def test_content_json_data_from_canonical_fields(db_session, storage):
    """content.json data values must match canonical.fields values."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    renderer = JSONRenderer()
    content = renderer.render(canonical)

    for field_id, cf in canonical.fields.items():
        if cf.value is not None:
            assert field_id in content.data
            assert content.data[field_id] == cf.value


# ─── 4. content.md block annotations ───


def test_content_md_block_annotations(db_session, storage):
    """Every canonical block must have a corresponding block_id comment in content.md."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    renderer = MarkdownRenderer()
    md = renderer.render(canonical)

    for block in canonical.blocks:
        assert f"<!-- block_id: {block.block_id}" in md
        assert block.text in md or block.text == ""


# ─── 5. chunks multi-chunk with small chunk_size ───


def test_chunks_multi_chunk_small_size(db_session, storage):
    """With small chunk_size, must produce at least 2 chunks, no text lost."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_policy_doc.json",
        "target_schema_policy.json",
        "mapping_template_policy.json",
    )

    renderer = ChunksRenderer()
    chunks = renderer.render(canonical, chunk_size=50)

    assert len(chunks.chunks) >= 2
    all_text = "\n".join(c.text for c in chunks.chunks)
    for block in canonical.blocks:
        if block.text:
            assert block.text in all_text

    canonical_block_ids = {b.block_id for b in canonical.blocks}
    for chunk in chunks.chunks:
        for sb in chunk.source_blocks:
            assert sb in canonical_block_ids


# ─── 6. Idempotent rendering ───


def test_idempotent_rendering(db_session, storage):
    """Same canonical rendered twice produces identical content and chunk_ids."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    render_svc = RenderService(db_session, storage)
    render_svc.render_all(task_id)
    cj1 = json.loads((storage.root / f"tasks/{task_id}/content.json").read_text(encoding="utf-8"))
    ck1 = json.loads((storage.root / f"tasks/{task_id}/chunks.json").read_text(encoding="utf-8"))

    render_svc.render_all(task_id)
    cj2 = json.loads((storage.root / f"tasks/{task_id}/content.json").read_text(encoding="utf-8"))
    ck2 = json.loads((storage.root / f"tasks/{task_id}/chunks.json").read_text(encoding="utf-8"))

    assert cj1 == cj2
    assert [c["chunk_id"] for c in ck1["chunks"]] == [c["chunk_id"] for c in ck2["chunks"]]


# ─── 7. Missing canonical blocks convert ───


def test_convert_without_canonical_fails(db_session, storage):
    """POST convert without prior canonical build should fail gracefully."""
    doc = Document(
        doc_id="doc_no_canonical", title="t", uir_version="1.0",
        storage_path="x.json", block_count=0,
    )
    db_session.add(doc)
    schema = TargetSchemaRecord(
        schema_id="s_no", name="s", version="1.0.0",
        schema_json='{"schema_id":"s_no","name":"s","version":"1.0.0","fields":[{"field_id":"f","name":"f","display_name":"F","type":"string"}]}',
        json_schema='{"type":"object","properties":{"f":{"type":"string"}}}',
    )
    db_session.add(schema)
    tpl = MappingTemplateRecord(
        template_id="t_no", schema_id="s_no", name="t", version="1.0.0",
        template_json='{"template_id":"t_no","schema_id":"s_no","name":"t","version":"1.0.0"}',
    )
    db_session.add(tpl)
    task = ConversionTask(
        task_id="task_no_canonical", doc_id="doc_no_canonical", schema_id="s_no",
        schema_version="1.0.0", template_id="t_no", template_version="1.0.0",
        status="mapping_completed", input_hash="sha256:x",
    )
    db_session.add(task)
    db_session.commit()

    render_svc = RenderService(db_session, storage)
    with pytest.raises(LookupError, match="canonical model not found"):
        render_svc.render_all("task_no_canonical")


# ─── 8. GET canonical returns persisted model ───


def test_get_canonical_returns_model(db_session, storage):
    """get_canonical returns the persisted CanonicalModel."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    svc = CanonicalService(db_session, storage)
    retrieved = svc.get_canonical(task_id)
    assert retrieved.task_id == canonical.task_id
    assert retrieved.doc_id == canonical.doc_id
    assert len(retrieved.fields) == len(canonical.fields)
    assert len(retrieved.blocks) == len(canonical.blocks)


# ─── 9. API routes exist in OpenAPI ───


def test_api_routes_in_openapi():
    """POST /convert and GET /canonical must exist in the app routes."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert any("/tasks/{task_id}/convert" in r for r in routes)
    assert any("/tasks/{task_id}/canonical" in r for r in routes)


# ─── 10. RenderService sets task status to rendered ───


def test_render_service_sets_rendered_status(db_session, storage):
    """After successful render_all, task status must be 'rendered'."""
    task_id, canonical, schema, template = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    render_svc = RenderService(db_session, storage)
    render_svc.render_all(task_id)

    task = db_session.get(ConversionTask, task_id)
    assert task.status == "rendered"
