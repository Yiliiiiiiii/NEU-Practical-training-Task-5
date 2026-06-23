import json
from datetime import datetime

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
    for status in ("draft", "pending"):
        db.add(KnowledgePackRecord(
            pack_id=f"kp_{status}",
            name=status.title(),
            scope_json=json.dumps({"template_id": "template_k"}),
            status=status,
            version="1.0.0",
            item_count=1,
            reviewer="tester",
        ))
        db.add(KnowledgePackItemRecord(
            item_id=f"kpi_{status}",
            pack_id=f"kp_{status}",
            item_type="alias_candidate",
            target_field_id="title",
            payload_json=json.dumps({"aliases": [f"{status}_title"]}),
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


def test_enum_map_candidates_merge_with_existing_keys(effective_context):
    db = effective_context
    db.add(KnowledgePackRecord(
        pack_id="kp_enum",
        name="Enum",
        scope_json=json.dumps({"template_id": "template_k"}),
        status="active",
        version="1.0.0",
        item_count=1,
        reviewer="tester",
    ))
    db.add(KnowledgePackItemRecord(
        item_id="kpi_enum",
        pack_id="kp_enum",
        item_type="enum_map_candidate",
        target_field_id="status",
        payload_json=json.dumps({"map": {"draft": "D", "published": "P"}}),
        source_candidate_id=None,
    ))
    db.commit()
    template = _template().model_copy(deep=True)
    template.enum_maps = {"status": {"draft": "OLD", "archived": "A"}}

    resolved, pack_ids = EffectiveTemplateService(db).resolve(template)

    assert resolved.enum_maps["status"] == {
        "draft": "OLD",
        "archived": "A",
        "published": "P",
    }
    assert pack_ids == ["kp_enum"]


def test_resolve_does_not_mutate_input_template(effective_context):
    db = effective_context
    db.add(KnowledgePackRecord(
        pack_id="kp_alias",
        name="Alias",
        scope_json=json.dumps({"schema_id": "schema_k"}),
        status="active",
        version="1.0.0",
        item_count=2,
        reviewer="tester",
    ))
    db.add_all([
        KnowledgePackItemRecord(
            item_id="kpi_alias_good",
            pack_id="kp_alias",
            item_type="alias_candidate",
            target_field_id="title",
            payload_json=json.dumps({"aliases": ["doc_title"]}),
            source_candidate_id=None,
        ),
        KnowledgePackItemRecord(
            item_id="kpi_alias_bad",
            pack_id="kp_alias",
            item_type="alias_candidate",
            target_field_id="title",
            payload_json=json.dumps({"aliases": ["valid_alias", 1, None]}),
            source_candidate_id=None,
        ),
    ])
    db.commit()
    template = _template()

    resolved, pack_ids = EffectiveTemplateService(db).resolve(template)

    assert template.aliases == {"title": ["title"]}
    assert resolved.aliases == {"title": ["title", "doc_title", "valid_alias"]}
    assert pack_ids == ["kp_alias"]


def test_malformed_enum_maps_are_ignored_without_dropping_valid_entries(effective_context):
    db = effective_context
    db.add(KnowledgePackRecord(
        pack_id="kp_enum_bad",
        name="Enum Bad",
        scope_json=json.dumps({"template_id": "template_k"}),
        status="active",
        version="1.0.0",
        item_count=2,
        reviewer="tester",
    ))
    db.add_all([
        KnowledgePackItemRecord(
            item_id="kpi_enum_invalid_map",
            pack_id="kp_enum_bad",
            item_type="enum_map_candidate",
            target_field_id="status",
            payload_json=json.dumps({"map": ["bad"]}),
            source_candidate_id=None,
        ),
        KnowledgePackItemRecord(
            item_id="kpi_enum_mixed_entries",
            pack_id="kp_enum_bad",
            item_type="enum_map_candidate",
            target_field_id="status",
            payload_json=json.dumps({"map": {
                "new": "N",
                "bad_value": 1,
                "none_value": None,
            }}),
            source_candidate_id=None,
        ),
    ])
    db.commit()
    template = _template().model_copy(deep=True)
    template.enum_maps = {"status": {"existing": "E"}}

    resolved, pack_ids = EffectiveTemplateService(db).resolve(template)

    assert resolved.enum_maps["status"] == {"existing": "E", "new": "N"}
    assert pack_ids == ["kp_enum_bad"]


def test_active_packs_and_items_use_stable_tie_ordering(effective_context):
    db = effective_context
    created_at = datetime(2026, 1, 1)
    for pack_id in ("kp_b", "kp_a"):
        db.add(KnowledgePackRecord(
            pack_id=pack_id,
            name=pack_id,
            scope_json=json.dumps({"template_id": "template_k"}),
            status="active",
            version="1.0.0",
            item_count=1,
            reviewer="tester",
            created_at=created_at,
        ))
    db.add_all([
        KnowledgePackItemRecord(
            item_id="kpi_b",
            pack_id="kp_a",
            item_type="alias_candidate",
            target_field_id="title",
            payload_json=json.dumps({"aliases": ["from_item_b"]}),
            source_candidate_id=None,
            created_at=created_at,
        ),
        KnowledgePackItemRecord(
            item_id="kpi_a",
            pack_id="kp_a",
            item_type="alias_candidate",
            target_field_id="title",
            payload_json=json.dumps({"aliases": ["from_item_a"]}),
            source_candidate_id=None,
            created_at=created_at,
        ),
        KnowledgePackItemRecord(
            item_id="kpi_c",
            pack_id="kp_b",
            item_type="alias_candidate",
            target_field_id="title",
            payload_json=json.dumps({"aliases": ["from_pack_b"]}),
            source_candidate_id=None,
            created_at=created_at,
        ),
    ])
    db.commit()

    resolved, pack_ids = EffectiveTemplateService(db).resolve(_template())

    assert pack_ids == ["kp_a", "kp_b"]
    assert resolved.aliases["title"] == [
        "title",
        "from_item_a",
        "from_item_b",
        "from_pack_b",
    ]
