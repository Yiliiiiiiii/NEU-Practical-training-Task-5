import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, CanonicalModelRecord, ConversionTask, TargetSchemaRecord
from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.chunks import Chunk, ChunksJSON
from app.schemas.content import ContentBlock, ContentJSON, ContentSchemaRef
from app.schemas.package import Manifest, ManifestFile
from app.schemas.target_schema import TargetField, TargetSchema
from app.services.package_service import PackageService
from app.services.storage_service import StorageService


@pytest.fixture()
def package_context(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        yield db, StorageService(tmp_path / "storage")


def _task(task_id: str, status: str) -> ConversionTask:
    return ConversionTask(
        task_id=task_id,
        doc_id="doc_package",
        schema_id="schema_package",
        schema_version="1.0.0",
        template_id="template_package",
        template_version="1.0.0",
        status=status,
        input_hash="sha256:test",
    )


def _manifest_file(path: str, raw: bytes) -> ManifestFile:
    return ManifestFile(
        path=path,
        required=True,
        media_type="application/octet-stream",
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
        role="content",
    )


def _manifest(files: list[ManifestFile]) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        package_id="pkg_integrity",
        package_version="1.0.0",
        task_id="task_integrity",
        doc_id="doc_integrity",
        created_at="2026-06-22T00:00:00+00:00",
        files=files,
        generator={"name": "test", "version": "1.0.0"},
    )


def test_manifest_verifier_rejects_unsafe_missing_corrupt_and_unsorted_files(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    raw = b"payload"
    (staging / "content.bin").write_bytes(raw)

    with pytest.raises(ValueError, match="unsafe manifest path"):
        PackageService._verify_manifest_files(
            staging,
            _manifest([_manifest_file("../escape.bin", raw)]),
        )
    with pytest.raises(ValueError, match="manifest file missing"):
        PackageService._verify_manifest_files(
            staging,
            _manifest([_manifest_file("missing.bin", raw)]),
        )

    wrong_size = _manifest_file("content.bin", raw)
    wrong_size.bytes += 1
    with pytest.raises(ValueError, match="manifest byte mismatch"):
        PackageService._verify_manifest_files(staging, _manifest([wrong_size]))

    wrong_hash = _manifest_file("content.bin", raw)
    wrong_hash.sha256 = "0" * 64
    with pytest.raises(ValueError, match="manifest sha256 mismatch"):
        PackageService._verify_manifest_files(staging, _manifest([wrong_hash]))

    (staging / "a.bin").write_bytes(raw)
    unsorted = [_manifest_file("content.bin", raw), _manifest_file("a.bin", raw)]
    with pytest.raises(ValueError, match="not sorted"):
        PackageService._verify_manifest_files(staging, _manifest(unsorted))

    (staging / "manifest.json").write_bytes(raw)
    self_included = [_manifest_file("manifest.json", raw)]
    with pytest.raises(ValueError, match="must not include itself"):
        PackageService._verify_manifest_files(staging, _manifest(self_included))


def _write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, raw in entries.items():
            archive.writestr(name, raw)


def test_zip_verifier_rejects_entry_set_unsafe_path_size_and_hash(tmp_path):
    raw = b"payload"
    manifest = _manifest([_manifest_file("content.bin", raw)])
    zip_path = tmp_path / "package.zip"

    _write_zip(zip_path, {"content.bin": raw})
    with pytest.raises(ValueError, match="entries do not match"):
        PackageService._verify_zip_payload(zip_path, manifest)

    unsafe_manifest = _manifest([_manifest_file("../content.bin", raw)])
    _write_zip(zip_path, {"../content.bin": raw, "manifest.json": b"{}"})
    with pytest.raises(ValueError, match="unsafe zip path"):
        PackageService._verify_zip_payload(zip_path, unsafe_manifest)

    wrong_size = _manifest_file("content.bin", raw)
    wrong_size.bytes += 1
    _write_zip(zip_path, {"content.bin": raw, "manifest.json": b"{}"})
    with pytest.raises(ValueError, match="zip byte mismatch"):
        PackageService._verify_zip_payload(zip_path, _manifest([wrong_size]))

    wrong_hash = _manifest_file("content.bin", raw)
    wrong_hash.sha256 = "f" * 64
    with pytest.raises(ValueError, match="zip sha256 mismatch"):
        PackageService._verify_zip_payload(zip_path, _manifest([wrong_hash]))


def test_package_service_rejects_invalid_state_and_missing_prerequisites(package_context):
    db, storage = package_context
    service = PackageService(db, storage)
    db.add_all([_task("task_failed", "failed"), _task("task_created", "created")])
    db.commit()

    with pytest.raises(ValueError, match="does not allow packaging"):
        service.create_package("task_failed")
    with pytest.raises(ValueError, match="not ready for packaging"):
        service.create_package("task_created")

    rendered = _task("task_missing_outputs", "rendered")
    db.add(rendered)
    db.commit()
    with pytest.raises(ValueError, match="rendered outputs are missing"):
        service.create_package(rendered.task_id)

    storage.save_json(f"tasks/{rendered.task_id}/content.json", {})
    storage.write_text(f"tasks/{rendered.task_id}/content.md", "")
    storage.save_json(f"tasks/{rendered.task_id}/chunks.json", {})
    with pytest.raises(LookupError, match="canonical model not found"):
        service.create_package(rendered.task_id)


def _seed_package(db, storage, task_id: str = "task_package") -> ConversionTask:
    task = _task(task_id, "rendered")
    schema = TargetSchema(
        schema_id=task.schema_id,
        name="Package schema",
        version="1.0.0",
        fields=[
            TargetField(
                field_id="title",
                name="title",
                display_name="Title",
                type="string",
                required=True,
            )
        ],
        json_schema={
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        },
    )
    canonical = CanonicalModel(
        canonical_version="1.0",
        task_id=task.task_id,
        doc_id=task.doc_id,
        schema_id=task.schema_id,
        fields={"title": CanonicalField(value="Document", type="string")},
        blocks=[
            CanonicalBlock(
                block_id="blk_1",
                type="paragraph",
                text="Body",
                source_blocks=["blk_1"],
            )
        ],
    )
    content = ContentJSON(
        doc_id=task.doc_id,
        task_id=task.task_id,
        schema_ref=ContentSchemaRef(schema_id=task.schema_id, version="1.0.0"),
        data={"title": "Document"},
        blocks=[ContentBlock(block_id="blk_1", type="paragraph", text="Body")],
    )
    chunks = ChunksJSON(
        doc_id=task.doc_id,
        task_id=task.task_id,
        chunks=[
            Chunk(
                chunk_id=f"chk_{task.task_id}_0",
                order=0,
                text="Body",
                source_blocks=["blk_1"],
            )
        ],
    )
    db.add_all(
        [
            task,
            TargetSchemaRecord(
                schema_id=schema.schema_id,
                name=schema.name,
                version=schema.version,
                schema_json=schema.model_dump_json(),
                json_schema=json.dumps(schema.json_schema),
            ),
            CanonicalModelRecord(
                task_id=task.task_id,
                doc_id=task.doc_id,
                schema_id=task.schema_id,
                model_json=canonical.model_dump_json(),
            ),
        ]
    )
    db.commit()
    storage.save_json(f"tasks/{task.task_id}/content.json", content.model_dump(mode="json"))
    storage.write_text(
        f"tasks/{task.task_id}/content.md",
        "<!-- block_id: blk_1 | source_blocks: blk_1 -->\nBody",
    )
    storage.save_json(f"tasks/{task.task_id}/chunks.json", chunks.model_dump(mode="json"))
    return task


def test_package_includes_assets_and_verifies_published_zip(package_context):
    db, storage = package_context
    task = _seed_package(db, storage)
    storage.write_text(f"tasks/{task.task_id}/assets/note.txt", "asset")

    result = PackageService(db, storage).create_package(task.task_id)

    with zipfile.ZipFile(storage.resolve(result["zip_path"])) as archive:
        assert "assets/note.txt" in archive.namelist()


def test_package_verification_failure_cleans_output_and_marks_task_failed(
    package_context,
    monkeypatch,
):
    db, storage = package_context
    task = _seed_package(db, storage, task_id="task_io_failure")

    def fail_verification(*_args):
        raise ValueError("simulated damaged package")

    monkeypatch.setattr(PackageService, "_verify_zip_payload", fail_verification)

    with pytest.raises(ValueError, match="failed to write or verify package zip"):
        PackageService(db, storage).create_package(task.task_id)

    db.refresh(task)
    assert task.status == "failed"
    assert task.error_code == "package_io_error"
    assert not list((storage.root / "packages").rglob("*.zip"))
