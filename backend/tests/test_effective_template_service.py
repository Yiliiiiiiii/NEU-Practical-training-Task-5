import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, KnowledgePackItemRecord, KnowledgePackRecord
from app.schemas.mapping_template import MappingTemplate
from app.services.effective_template_service import EffectiveTemplateService


@pytest.fixture()
def effective_context():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        yield db


def _template() -> MappingTemplate:
    return MappingTemplate(
        template_id="template_k",
        schema_id="schema_k",
        name="Base",
        version="1.0.0",
        aliases={"title": ["title"]},
        regex_rules=[],
        transform_rules=[],
        defaults={},
        enum_maps={},
    )


def test_pending_or_draft_packs_do_not_change_effective_template(effective_context):
    db = effective_context
    db.add(KnowledgePackRecord(
        pack_id="kp_draft",
        name="Draft",
        scope_json=json.dumps({"template_id": "template_k"}),
        status="draft",
        version="1.0.0",
        item_count=1,
        reviewer="tester",
    ))
    db.add(KnowledgePackItemRecord(
        item_id="kpi_draft",
        pack_id="kp_draft",
        item_type="alias_candidate",
        target_field_id="title",
        payload_json=json.dumps({"aliases": ["doc_title"]}),
        source_candidate_id=None,
    ))
    db.commit()

    resolved, pack_ids = EffectiveTemplateService(db).resolve(_template())

    assert resolved.aliases == {"title": ["title"]}
    assert pack_ids == []


def test_active_pack_merges_aliases_without_duplicates(effective_context):
    db = effective_context
    db.add(KnowledgePackRecord(
        pack_id="kp_active",
        name="Active",
        scope_json=json.dumps({"schema_id": "schema_k", "template_id": "template_k"}),
        status="active",
        version="1.0.0",
        item_count=1,
        reviewer="tester",
    ))
    db.add(KnowledgePackItemRecord(
        item_id="kpi_active",
        pack_id="kp_active",
        item_type="alias_candidate",
        target_field_id="title",
        payload_json=json.dumps({"aliases": ["title", "doc_title"]}),
        source_candidate_id=None,
    ))
    db.commit()

    resolved, pack_ids = EffectiveTemplateService(db).resolve(_template())

    assert resolved.aliases["title"] == ["title", "doc_title"]
    assert pack_ids == ["kp_active"]
