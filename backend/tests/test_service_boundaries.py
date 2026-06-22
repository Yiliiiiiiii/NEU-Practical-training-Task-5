import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    ConversionTask,
    Document,
    FieldMappingRecord,
    MappingTemplateRecord,
    ReviewRecord,
    TargetSchemaRecord,
)
from app.schemas.api import MappingReviewItem
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRBlock, UIRDocument
from app.services.conversion_service import ConversionService
from app.services.document_service import DocumentService
from app.services.review_service import ReviewService
from app.services.schema_service import SchemaService
from app.services.storage_service import StorageService


@pytest.fixture()
def service_context(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        yield db, StorageService(tmp_path / "storage")


def _schema(schema_id: str = "schema_service", name: str = "Schema") -> TargetSchema:
    return TargetSchema(
        schema_id=schema_id,
        name=name,
        version="1.0.0",
        fields=[
            TargetField(
                field_id="title",
                name="title",
                display_name="Title",
                type="string",
            )
        ],
        json_schema={"type": "object", "properties": {"title": {"type": "string"}}},
    )


def test_document_service_title_fallbacks_and_non_object_storage(service_context):
    db, storage = service_context
    service = DocumentService(db, storage)
    heading = UIRDocument(
        uir_version="1.0",
        doc_id="doc_heading",
        blocks=[UIRBlock(block_id="h", type="heading", level=1, text="Heading title")],
    )
    no_title = UIRDocument(uir_version="1.0", doc_id="doc_none")

    assert service._extract_title(heading) == "Heading title"
    assert service._extract_title(no_title) is None

    record = Document(
        doc_id="doc_invalid",
        uir_version="1.0",
        storage_path="documents/doc_invalid/uir.json",
        block_count=0,
    )
    storage.save_json(record.storage_path, ["not", "an", "object"])
    with pytest.raises(ValueError, match="must be a JSON object"):
        service.read_uir(record)


def test_document_import_without_source_and_paginated_listing(service_context):
    db, storage = service_context
    service = DocumentService(db, storage)
    first = UIRDocument(
        uir_version="1.0",
        doc_id="doc_first",
        metadata={"title": "First"},
    )
    second = UIRDocument(
        uir_version="1.0",
        doc_id="doc_second",
        metadata={"title": "Second"},
    )

    service.import_uir(first)
    service.import_uir(second)
    items, total = service.list_documents(page=2, page_size=1)

    assert total == 2
    assert len(items) == 1
    assert db.get(Document, "doc_first").source_name is None


def test_schema_service_updates_existing_record(service_context):
    db, storage = service_context
    service = SchemaService(db, storage)
    service.create_schema(_schema())

    updated = service.create_schema(_schema(name="Updated schema"))

    assert updated.name == "Updated schema"
    assert len(service.list_schemas()) == 1
    assert service.get_schema("schema_service") is updated
    assert service.parse_schema(updated).name == "Updated schema"


def _task(task_id: str, status: str = "mapping_completed") -> ConversionTask:
    return ConversionTask(
        task_id=task_id,
        doc_id="doc_service",
        schema_id="schema_service",
        schema_version="1.0.0",
        template_id="template_service",
        template_version="1.0.0",
        status=status,
        input_hash="sha256:test",
    )


def test_review_service_covers_decisions_remaining_review_and_identity_guard(service_context):
    db, _ = service_context
    task = _task("task_review", status="review_required")
    db.add(task)
    mappings = [
        FieldMappingRecord(
            mapping_id=f"mapping_{index}",
            task_id=task.task_id,
            candidate_id=f"candidate_{index}",
            target_field_id=f"target_{index}",
            method="fuzzy_match",
            confidence=0.5,
            status="pending_review",
            need_review=True,
        )
        for index in range(4)
    ]
    db.add_all(mappings)
    db.commit()
    service = ReviewService(db)

    updated = service.save_mapping_reviews(
        task.task_id,
        [
            MappingReviewItem(
                mapping_id="mapping_0",
                decision="changed",
                new_target_field_id="renamed",
            ),
            MappingReviewItem(mapping_id="mapping_1", decision="rejected"),
            MappingReviewItem(mapping_id="mapping_2", decision="custom"),
        ],
    )

    assert updated == 3
    assert task.status == "review_required"
    assert mappings[0].target_field_id == "renamed"
    assert [mapping.status for mapping in mappings[:3]] == [
        "confirmed",
        "rejected",
        "reviewed",
    ]
    assert db.query(ReviewRecord).count() == 3

    service.save_mapping_reviews(
        task.task_id,
        [MappingReviewItem(mapping_id="mapping_3", decision="confirmed")],
    )
    assert task.status == "mapping_completed"

    foreign = FieldMappingRecord(
        mapping_id="foreign",
        task_id="another_task",
        candidate_id="candidate_foreign",
        target_field_id="target",
        method="exact_match",
        confidence=1.0,
        status="confirmed",
        need_review=False,
    )
    db.add(foreign)
    db.commit()
    with pytest.raises(LookupError, match="mapping not found"):
        service.save_mapping_reviews(
            task.task_id,
            [MappingReviewItem(mapping_id="foreign")],
        )


def test_conversion_service_reports_missing_schema_and_template(service_context):
    db, storage = service_context
    missing_schema = _task("task_missing_schema")
    db.add(missing_schema)
    db.commit()
    service = ConversionService(db, storage)

    with pytest.raises(LookupError, match="schema not found"):
        service.convert(missing_schema.task_id, render_outputs=True, chunk_size=500)

    schema = _schema()
    db.add(
        TargetSchemaRecord(
            schema_id=schema.schema_id,
            name=schema.name,
            version=schema.version,
            schema_json=schema.model_dump_json(),
            json_schema=json.dumps(schema.json_schema),
        )
    )
    db.commit()
    with pytest.raises(LookupError, match="template not found"):
        service.convert(missing_schema.task_id, render_outputs=True, chunk_size=500)


def test_conversion_service_render_branch_delegates_and_returns_outputs(service_context):
    db, storage = service_context
    schema = _schema()
    task = _task("task_render")
    template_json = {
        "template_id": "template_service",
        "schema_id": schema.schema_id,
        "name": "Template",
        "version": "1.0.0",
    }
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
            MappingTemplateRecord(
                template_id="template_service",
                schema_id=schema.schema_id,
                name="Template",
                version="1.0.0",
                template_json=json.dumps(template_json),
            ),
        ]
    )
    db.commit()
    service = ConversionService(db, storage)

    class CanonicalStub:
        def build_canonical(self, *_args):
            return object()

    class RenderStub:
        def render_all(self, task_id: str, chunk_size: int):
            assert task_id == task.task_id
            assert chunk_size == 321
            return ["content.json", "content.md", "chunks.json"]

    service.canonical_service = CanonicalStub()
    service.render_service = RenderStub()

    status, outputs = service.convert(task.task_id, render_outputs=True, chunk_size=321)

    assert status == "rendered"
    assert outputs == ["content.json", "content.md", "chunks.json"]
