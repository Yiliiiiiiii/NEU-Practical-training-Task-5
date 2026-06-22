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
from app.engines.canonical_builder import CanonicalBuilder
from app.schemas.canonical import CanonicalField
from app.schemas.uir import UIRAsset, UIRBlock, UIRDocument
from app.services.canonical_service import CanonicalService
from app.services.storage_service import StorageService


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


def test_canonical_builder_preserves_blocks():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_1",
        metadata={"title": "test"},
        blocks=[
            UIRBlock(block_id="blk_1", type="heading", level=1, text="Chapter 1"),
            UIRBlock(block_id="blk_2", type="paragraph", text="Hello world"),
        ],
        assets=[
            UIRAsset(
                asset_id="asset_1", type="image",
                path="img.png", source_block_id="blk_1",
            )
        ],
    )
    fields = {
        "title": CanonicalField(value="test", type="string"),
    }

    builder = CanonicalBuilder()
    model = builder.build(
        task_id="task_1",
        doc_id="doc_1",
        schema_id="schema_1",
        fields=fields,
        uir=uir,
    )

    assert model.task_id == "task_1"
    assert model.doc_id == "doc_1"
    assert model.schema_id == "schema_1"
    assert len(model.blocks) == 2
    assert model.blocks[0].block_id == "blk_1"
    assert model.blocks[0].source_blocks == ["blk_1"]
    assert model.blocks[0].text_hash is not None
    assert len(model.assets) == 1
    assert model.assets[0].asset_id == "asset_1"
    assert model.doc_meta == {"title": "test"}


def test_canonical_builder_empty_uir():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_1",
        metadata={},
        blocks=[],
        assets=[],
    )

    builder = CanonicalBuilder()
    model = builder.build(
        task_id="task_1",
        doc_id="doc_1",
        schema_id="schema_1",
        fields={},
        uir=uir,
    )

    assert model.blocks == []
    assert model.assets == []
    assert model.fields == {}


def test_canonical_service_builds_and_persists(db_session, storage):
    uir_data = {
        "uir_version": "1.0",
        "doc_id": "doc_1",
        "metadata": {"title": "Test Doc", "author": "Author"},
        "blocks": [
            {"block_id": "blk_1", "type": "heading", "level": 1, "text": "Title", "attributes": {}},
            {"block_id": "blk_2", "type": "paragraph", "text": "Content here.", "attributes": {}},
        ],
        "assets": [],
        "normalization_records": [],
    }
    storage.save_json("documents/doc_1/uir.json", uir_data)

    doc = Document(
        doc_id="doc_1",
        title="Test Doc",
        uir_version="1.0",
        storage_path="documents/doc_1/uir.json",
        block_count=2,
    )
    db_session.add(doc)

    schema = TargetSchemaRecord(
        schema_id="schema_1",
        name="Test Schema",
        version="1.0.0",
        schema_json=(
            '{"schema_id":"schema_1","name":"Test Schema",'
            '"version":"1.0.0","fields":[{"field_id":"title",'
            '"name":"title","display_name":"Title","type":"string",'
            '"required":true}]}'
        ),
        json_schema=(
            '{"type":"object","required":["title"],'
            '"properties":{"title":{"type":"string"}}}'
        ),
    )
    db_session.add(schema)

    template = MappingTemplateRecord(
        template_id="tpl_1",
        schema_id="schema_1",
        name="Test Template",
        version="1.0.0",
        template_json=(
            '{"template_id":"tpl_1","schema_id":"schema_1",'
            '"name":"Test Template","version":"1.0.0",'
            '"aliases":{},"regex_rules":[],"transform_rules":[],'
            '"defaults":{},"enum_maps":{}}'
        ),
    )
    db_session.add(template)

    task = ConversionTask(
        task_id="task_1",
        doc_id="doc_1",
        schema_id="schema_1",
        schema_version="1.0.0",
        template_id="tpl_1",
        template_version="1.0.0",
        status="mapping_completed",
        input_hash="sha256:abc123",
    )
    db_session.add(task)

    candidate = FieldCandidateRecord(
        candidate_id="cand_1",
        task_id="task_1",
        doc_id="doc_1",
        source_path="metadata.title",
        source_name="title",
        display_name="title",
        value_sample='"Test Doc"',
        inferred_type="string",
        source_blocks_json="[]",
        confidence=0.95,
    )
    db_session.add(candidate)

    mapping = FieldMappingRecord(
        mapping_id="map_1",
        task_id="task_1",
        candidate_id="cand_1",
        target_field_id="title",
        method="exact_match",
        confidence=1.0,
        status="confirmed",
        need_review=False,
        evidence_json='["source_name equals target name"]',
    )
    db_session.add(mapping)
    db_session.commit()

    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema

    schema_obj = TargetSchema.model_validate_json(schema.schema_json)
    template_obj = MappingTemplate.model_validate_json(template.template_json)

    service = CanonicalService(db_session, storage)
    canonical = service.build_canonical("task_1", schema_obj, template_obj)

    assert canonical.task_id == "task_1"
    assert "title" in canonical.fields
    assert canonical.fields["title"].value == "Test Doc"
    assert len(canonical.blocks) == 2
    assert canonical.blocks[0].block_id == "blk_1"

    retrieved = service.get_canonical("task_1")
    assert retrieved.fields["title"].value == "Test Doc"


def test_canonical_service_raises_on_missing_task(db_session, storage):
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema

    schema = TargetSchema(
        schema_id="s1", name="s", version="1.0.0",
        fields=[{"field_id": "title", "name": "title", "display_name": "Title", "type": "string"}],
    )
    template = MappingTemplate(
        template_id="t1", schema_id="s1", name="t", version="1.0.0",
    )
    service = CanonicalService(db_session, storage)
    with pytest.raises(LookupError, match="task not found"):
        service.build_canonical("nonexistent", schema, template)
