import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.engines.field_candidate_engine import FieldCandidateEngine
from app.engines.mapping_engine import MappingEngine
from app.main import app
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.services.canonical_service import CanonicalService
from app.services.render_service import RenderService
from app.services.storage_service import StorageService
from app.verifiers.package_verifier import PackageVerifierIssue, PackageVerifierReport

EXAMPLES = Path(__file__).resolve().parent.parent.parent / "examples" / "demo"


def _load_json(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    with TestSession() as session:
        yield session


@pytest.fixture()
def storage(tmp_path):
    return StorageService(tmp_path / "storage")


@pytest.fixture()
def client(db_session, storage, monkeypatch):
    from app.api import deps

    def override_get_db():
        yield db_session

    def override_get_storage():
        return storage

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_storage_service] = override_get_storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


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

    from app.schemas.uir import UIRDocument
    uir = UIRDocument.model_validate(uir_data)
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

    mapping_engine = MappingEngine()
    target_schema = TargetSchema.model_validate(schema_data)
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
    canonical_svc.build_canonical(task_id, target_schema, template_obj)

    render_svc = RenderService(db_session, storage)
    render_svc.render_all(task_id)

    return task_id


# ─── 1. General demo E2E: full pipeline through API ───


def test_general_demo_full_pipeline(client, db_session, storage):
    """General demo: import → candidates → mapping → convert → package → download → unzip."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={"package_version": "1.0.0"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["package_id"]
    zip_path = data["zip_path"]
    assert "standard_package.zip" in zip_path

    resp = client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "X-SHA256" in resp.headers

    zip_bytes = resp.content
    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "content.json" in names
        assert "content.md" in names
        assert "chunks.json" in names
        assert "manifest.json" in names
        assert "metadata.json" in names
        assert "config_snapshot.json" in names
        assert "validation_report.json" in names
        assert "consistency_report.json" in names
        assert "trace.json" in names

        manifest = json.loads(zf.read("manifest.json"))
        assert "manifest.json" not in [f["path"] for f in manifest["files"]]
        for f in manifest["files"]:
            raw = zf.read(f["path"])
            assert hashlib.sha256(raw).hexdigest() == f["sha256"]
            assert len(raw) == f["bytes"]

        cj = json.loads(zf.read("content.json"))
        assert cj["content_version"] == "1.1"
        assert "data" in cj
        assert len(cj["blocks"]) > 0


# ─── 2. Policy demo E2E ───


def test_policy_demo_full_pipeline(client, db_session, storage):
    """Policy demo: package with date/enum/merge, validate ZIP contents."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_policy_doc.json",
        "target_schema_policy.json",
        "mapping_template_policy.json",
    )

    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"

    resp = client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert resp.status_code == 200

    zip_bytes = resp.content
    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes)) as zf:
        cj = json.loads(zf.read("content.json"))
        assert "title" in cj["data"] or "publish_org" in cj["data"]
        cm = zf.read("content.md").decode("utf-8")
        assert "block_id:" in cm
        ck = json.loads(zf.read("chunks.json"))
        assert len(ck["chunks"]) >= 1


# ─── 3. Validation required/type/enum ───


def test_validation_required_missing():
    """Validation catches required field missing."""
    from app.validators.content_validator import validate_content_data
    schema = TargetSchema(
        schema_id="s", name="s", version="1.0.0",
        fields=[{"field_id": "title", "name": "title", "display_name": "Title",
                 "type": "string", "required": True}],
        json_schema={"type": "object", "required": ["title"],
                     "properties": {"title": {"type": "string"}}},
    )
    report = validate_content_data("t", "s", {}, schema)
    assert not report.passed
    assert any(i.code == "required_missing" for i in report.issues)


def test_validation_honors_field_required_without_json_schema_required():
    """Field.required is enforced even when json_schema.required is omitted."""
    from app.validators.content_validator import validate_content_data
    schema = TargetSchema(
        schema_id="s", name="s", version="1.0.0",
        fields=[{"field_id": "title", "name": "title", "display_name": "Title",
                 "type": "string", "required": True}],
        json_schema={"type": "object",
                     "properties": {"title": {"type": "string"}}},
    )
    report = validate_content_data("t", "s", {}, schema)
    assert not report.passed
    assert any(i.code == "required_missing" and i.path == "data.title"
               for i in report.issues)


def test_validation_type_mismatch():
    """Validation catches type mismatch."""
    from app.validators.content_validator import validate_content_data
    schema = TargetSchema(
        schema_id="s", name="s", version="1.0.0",
        fields=[{"field_id": "count", "name": "count", "display_name": "Count",
                 "type": "integer", "required": False}],
        json_schema={"type": "object",
                     "properties": {"count": {"type": "integer"}}},
    )
    report = validate_content_data("t", "s", {"count": "not_a_number"}, schema)
    assert report.passed
    assert any(i.code == "type_mismatch" for i in report.issues)


def test_validation_integer_rejects_bool():
    """Python bool values must not satisfy integer fields."""
    from app.validators.content_validator import validate_content_data
    schema = TargetSchema(
        schema_id="s", name="s", version="1.0.0",
        fields=[{"field_id": "count", "name": "count", "display_name": "Count",
                 "type": "integer", "required": False}],
        json_schema={"type": "object",
                     "properties": {"count": {"type": "integer"}}},
    )
    report = validate_content_data("t", "s", {"count": True}, schema)
    assert any(i.code == "type_mismatch" for i in report.issues)


def test_validation_enum_violation():
    """Validation catches enum violation."""
    from app.validators.content_validator import validate_content_data
    schema = TargetSchema(
        schema_id="s", name="s", version="1.0.0",
        fields=[{"field_id": "status", "name": "status", "display_name": "Status",
                 "type": "string", "required": True, "constraints": {}}],
        json_schema={"type": "object", "required": ["status"],
                     "properties": {"status": {"type": "string",
                                               "enum": ["active", "inactive"]}}},
    )
    report = validate_content_data("t", "s", {"status": "unknown"}, schema)
    assert not report.passed
    assert any(i.code == "enum_violation" for i in report.issues)


# ─── 4. Consistency broken source_blocks → critical error ───


def test_validation_numeric_range_and_date_format():
    """Validation catches numeric range and invalid date values."""
    from app.validators.content_validator import validate_content_data
    schema = TargetSchema(
        schema_id="s", name="s", version="1.0.0",
        fields=[
            {"field_id": "score", "name": "score", "display_name": "Score",
             "type": "float", "required": False},
            {"field_id": "publish_date", "name": "publish_date",
             "display_name": "Publish Date", "type": "date", "required": False},
        ],
        json_schema={
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "publish_date": {"type": "string", "format": "date"},
            },
        },
    )
    report = validate_content_data(
        "t",
        "s",
        {"score": 101, "publish_date": "2026-99-99"},
        schema,
    )
    assert any(i.code == "maximum_violation" for i in report.issues)
    assert any(i.code == "date_format_mismatch" for i in report.issues)


def test_consistency_broken_source_blocks():
    """Broken chunk source_blocks produces critical error."""
    from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
    from app.schemas.chunks import Chunk, ChunksJSON
    from app.schemas.content import ContentBlock, ContentJSON, ContentSchemaRef
    from app.validators.consistency_validator import validate_consistency

    canonical = CanonicalModel(
        canonical_version="1.0", task_id="t", doc_id="d", schema_id="s",
        fields={"title": CanonicalField(value="test", type="string")},
        blocks=[CanonicalBlock(block_id="blk_1", type="paragraph", text="hello",
                               source_blocks=["blk_1"], text_hash="sha256:abc")],
    )
    content_json = ContentJSON(
        doc_id="d", task_id="t",
        schema_ref=ContentSchemaRef(schema_id="s", version="1.0.0"),
        data={"title": "test"},
        blocks=[ContentBlock(block_id="blk_1", type="paragraph", text="hello",
                             source_blocks=["blk_1"])],
    )
    content_md = "<!-- block_id: blk_1 | source_blocks: blk_1 -->\nhello"
    chunks = ChunksJSON(
        doc_id="d", task_id="t",
        chunks=[Chunk(chunk_id="chk_t_0", order=0, text="hello",
                      source_blocks=["NONEXISTENT"], text_hash="sha256:abc")],
    )

    report = validate_consistency("t", content_json, content_md, chunks, canonical)
    assert not report.passed
    assert any(c.check_name == "chunk_source_blocks_backlink" and not c.passed
               for c in report.checks)


# ─── 5. Manifest excludes self, correct SHA-256 ───


def test_consistency_detects_block_order_mismatch():
    """content.json block order must match canonical block order."""
    from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
    from app.schemas.chunks import Chunk, ChunksJSON
    from app.schemas.content import ContentBlock, ContentJSON, ContentSchemaRef
    from app.validators.consistency_validator import validate_consistency

    canonical = CanonicalModel(
        canonical_version="1.0", task_id="t", doc_id="d", schema_id="s",
        fields={"title": CanonicalField(value="test", type="string")},
        blocks=[
            CanonicalBlock(block_id="blk_1", type="paragraph", text="one",
                           source_blocks=["blk_1"], text_hash="sha256:1"),
            CanonicalBlock(block_id="blk_2", type="paragraph", text="two",
                           source_blocks=["blk_2"], text_hash="sha256:2"),
        ],
    )
    content_json = ContentJSON(
        doc_id="d", task_id="t",
        schema_ref=ContentSchemaRef(schema_id="s", version="1.0.0"),
        data={"title": "test"},
        blocks=[
            ContentBlock(block_id="blk_2", type="paragraph", text="two",
                         source_blocks=["blk_2"]),
            ContentBlock(block_id="blk_1", type="paragraph", text="one",
                         source_blocks=["blk_1"]),
        ],
    )
    content_md = (
        "<!-- block_id: blk_1 | source_blocks: blk_1 -->\none\n"
        "<!-- block_id: blk_2 | source_blocks: blk_2 -->\ntwo"
    )
    chunks = ChunksJSON(
        doc_id="d", task_id="t",
        chunks=[
            Chunk(chunk_id="chk_t_0", order=0, text="one\ntwo",
                  source_blocks=["blk_1", "blk_2"], text_hash="sha256:abc")
        ],
    )

    report = validate_consistency("t", content_json, content_md, chunks, canonical)
    assert not report.passed
    assert any(c.check_name == "block_order_consistency" and not c.passed
               for c in report.checks)


def test_manifest_excludes_self_and_correct_sha(tmp_path):
    """Manifest does not include itself, SHA-256 matches real bytes."""
    from app.engines.manifest_engine import generate_manifest

    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "content.json").write_text('{"data":{}}', encoding="utf-8")
    (staging / "content.md").write_text("# test", encoding="utf-8")
    (staging / "manifest.json").write_text('{"files":[]}', encoding="utf-8")

    manifest = generate_manifest("t", "d", "pkg_1", staging)
    paths = [f.path for f in manifest.files]
    assert "manifest.json" not in paths
    assert "content.json" in paths

    for f in manifest.files:
        raw = (staging / f.path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == f.sha256
        assert len(raw) == f.bytes


# ─── 6. ZIP no unsafe paths ───


def test_zip_no_unsafe_paths(client, db_session, storage):
    """ZIP entries have no absolute paths, drive letters, or .. traversal."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    client.post(f"/api/v1/tasks/{task_id}/package", json={})
    resp = client.get(f"/api/v1/tasks/{task_id}/package/download")
    zip_bytes = resp.content

    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            assert not name.startswith("/")
            assert ":" not in name
            assert ".." not in name
            assert "\\" not in name


# ─── 7. Consistency critical blocks packaging ───


def test_consistency_critical_blocks_packaging(client, db_session, storage):
    """Consistency failure prevents packaging, returns 409."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    chunks_path = storage.resolve(f"tasks/{task_id}/chunks.json")
    chunks_data = json.loads(chunks_path.read_text(encoding="utf-8"))
    for chunk in chunks_data["chunks"]:
        chunk["source_blocks"] = ["NONEXISTENT_BLOCK"]
    chunks_path.write_text(json.dumps(chunks_data, ensure_ascii=False), encoding="utf-8")

    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert resp.status_code == 409


# ─── 8. GET validation report via API ───


def test_get_validation_report_api(client, db_session, storage):
    """GET /reports/validation returns validation report."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    client.post(f"/api/v1/tasks/{task_id}/package", json={})
    resp = client.get(f"/api/v1/tasks/{task_id}/reports/validation")
    assert resp.status_code == 200
    data = resp.json()
    assert "passed" in data
    assert "issues" in data
    assert "summary" in data


# ─── 9. GET consistency report via API ───


def test_get_consistency_report_api(client, db_session, storage):
    """GET /reports/consistency returns consistency report."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    client.post(f"/api/v1/tasks/{task_id}/package", json={})
    resp = client.get(f"/api/v1/tasks/{task_id}/reports/consistency")
    assert resp.status_code == 200
    data = resp.json()
    assert "passed" in data
    assert "checks" in data


def test_get_package_verifier_report_api(client, db_session, storage):
    """GET /reports/package-verifier returns the external verifier report."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    client.post(f"/api/v1/tasks/{task_id}/package", json={})
    resp = client.get(f"/api/v1/tasks/{task_id}/reports/package-verifier")
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["issues"] == []
    assert data["summary"]["verified_payloads"] >= 1


# ─── 10. GET trace via API ───


def test_get_trace_api(client, db_session, storage):
    """GET /trace returns trace events."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    resp = client.get(f"/api/v1/tasks/{task_id}/trace")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert isinstance(data["events"], list)


# ─── 11. Package not found → 404 ───


def test_package_download_not_found(client, db_session):
    """GET /package/download for nonexistent task returns 404."""
    resp = client.get("/api/v1/tasks/nonexistent/package/download")
    assert resp.status_code == 404


# ─── 12. Duplicate package request (idempotency) ───


def test_duplicate_package_idempotent(client, db_session, storage):
    """Second package request overwrites previous, still completed."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    r1 = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert r1.status_code == 200
    pkg_id_1 = r1.json()["package_id"]

    r2 = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert r2.status_code == 200
    pkg_id_2 = r2.json()["package_id"]

    assert pkg_id_1 != pkg_id_2
    resp = client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert resp.status_code == 200


def test_package_blocks_validation_errors(client, db_session, storage):
    """Validation errors prevent completed packages and leave no downloadable zip."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    content_path = storage.resolve(f"tasks/{task_id}/content.json")
    content_data = json.loads(content_path.read_text(encoding="utf-8"))
    content_data["data"]["title"] = ""
    content_path.write_text(json.dumps(content_data, ensure_ascii=False), encoding="utf-8")

    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert resp.status_code == 409
    task = db_session.get(ConversionTask, task_id)
    assert task.status == "failed"
    assert task.error_code == "validation_error"

    resp = client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert resp.status_code == 404


def test_package_records_trace_event_and_exports_trace_json(client, db_session, storage):
    """Successful packaging records package-stage trace and exports it into trace.json."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert resp.status_code == 200

    trace_data = storage.read_json(f"tasks/{task_id}/trace.json")
    assert any(
        event["stage"] == "package" and event["action"] == "create_package"
        for event in trace_data["events"]
    )


def test_requested_package_version_is_written_to_metadata_and_manifest(
    client, db_session, storage
):
    """Requested package_version is consistent in metadata.json and manifest.json."""
    task_id = _seed_full_pipeline(
        db_session, storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )
    resp = client.post(
        f"/api/v1/tasks/{task_id}/package",
        json={"package_version": "1.2.3"},
    )
    assert resp.status_code == 200
    resp = client.get(f"/api/v1/tasks/{task_id}/package/download")

    with zipfile.ZipFile(__import__("io").BytesIO(resp.content)) as zf:
        metadata = json.loads(zf.read("metadata.json"))
        manifest = json.loads(zf.read("manifest.json"))
    assert metadata["package_version"] == "1.2.3"
    assert manifest["package_version"] == "1.2.3"


def test_package_service_saves_external_verifier_report_outside_zip(
    client, db_session, storage
):
    """Phase 10 verifier report is persisted outside the standard package ZIP."""
    task_id = _seed_full_pipeline(
        db_session,
        storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={})
    assert resp.status_code == 200

    verifier_report = storage.read_json(f"tasks/{task_id}/package_verifier_report.json")
    assert verifier_report["passed"] is True
    assert verifier_report["summary"]["verified_payloads"] >= 1

    download = client.get(f"/api/v1/tasks/{task_id}/package/download")
    assert download.status_code == 200
    with zipfile.ZipFile(__import__("io").BytesIO(download.content)) as zf:
        assert "package_verifier_report.json" not in zf.namelist()


def test_package_service_blocks_completion_when_external_verifier_rejects_zip(
    client, db_session, storage, monkeypatch
):
    """A verifier failure prevents completed package records and removes the ZIP."""
    task_id = _seed_full_pipeline(
        db_session,
        storage,
        "example_uir_general_doc.json",
        "target_schema_general.json",
        "mapping_template_general.json",
    )

    def reject_package(zip_path, *, max_json_bytes=5_000_000):
        return PackageVerifierReport(
            passed=False,
            zip_path=str(zip_path),
            zip_sha256=None,
            summary={},
            issues=[
                PackageVerifierIssue(
                    code="forced_reject",
                    message="forced verifier rejection",
                    path="content.json",
                )
            ],
        )

    monkeypatch.setattr("app.services.package_service.verify_package_zip", reject_package)

    resp = client.post(f"/api/v1/tasks/{task_id}/package", json={})

    assert resp.status_code == 409
    task = db_session.get(ConversionTask, task_id)
    assert task.status == "failed"
    assert task.error_code == "package_verifier_error"
    packages_dir = storage.resolve("packages")
    assert not packages_dir.exists() or not list(packages_dir.rglob("*.zip"))
