import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients.llm_client import LLMClient, LLMSuggestion
from app.db.models import (
    Base,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.services.mapping_service import MappingService
from app.services.storage_service import StorageService


@pytest.fixture()
def mapping_context(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    storage = StorageService(tmp_path / "storage")
    with factory() as db:
        yield db, storage


def _seed_unmapped_task(db) -> str:
    schema = {
        "schema_id": "schema_llm",
        "name": "LLM fallback schema",
        "version": "1.0.0",
        "fields": [
            {
                "field_id": "approval_unit",
                "name": "approval_unit",
                "display_name": "Approval Unit",
                "type": "string",
                "required": True,
            }
        ],
        "json_schema": {
            "type": "object",
            "required": ["approval_unit"],
            "properties": {"approval_unit": {"type": "string"}},
        },
    }
    template = {
        "template_id": "template_llm",
        "schema_id": "schema_llm",
        "name": "LLM fallback template",
        "version": "1.0.0",
        "aliases": {},
        "regex_rules": [],
        "transform_rules": [],
        "defaults": {},
        "enum_maps": {},
    }
    db.add(Document(
        doc_id="doc_llm",
        title="doc",
        uir_version="1.0",
        source_name="doc.json",
        storage_path="documents/doc_llm/uir.json",
        block_count=0,
    ))
    db.add(TargetSchemaRecord(
        schema_id="schema_llm",
        name=schema["name"],
        version=schema["version"],
        schema_json=json.dumps(schema, ensure_ascii=False),
        json_schema=json.dumps(schema["json_schema"], ensure_ascii=False),
    ))
    db.add(MappingTemplateRecord(
        template_id="template_llm",
        schema_id="schema_llm",
        name=template["name"],
        version=template["version"],
        template_json=json.dumps(template, ensure_ascii=False),
    ))
    db.add(ConversionTask(
        task_id="task_llm",
        doc_id="doc_llm",
        schema_id="schema_llm",
        schema_version="1.0.0",
        template_id="template_llm",
        template_version="1.0.0",
        status="candidates_ready",
        input_hash="sha256:test",
        options_json="{}",
    ))
    db.add(FieldCandidateRecord(
        candidate_id="cand_approval",
        task_id="task_llm",
        doc_id="doc_llm",
        source_path="metadata.issuer_text",
        source_name="issuer_text",
        display_name="Issuer Text",
        value_sample=json.dumps("由市发展改革委批准发布", ensure_ascii=False),
        inferred_type="string",
        source_blocks_json='["blk_1"]',
        confidence=0.7,
    ))
    db.commit()
    return "task_llm"


def _seed_autogenerate_task(db, storage: StorageService) -> str:
    uir = {
        "uir_version": "1.0",
        "doc_id": "doc_auto",
        "metadata": {"doc_title": "Auto Candidate Title"},
        "blocks": [],
        "assets": [],
    }
    storage.save_json("documents/doc_auto/uir.json", uir)
    schema = {
        "schema_id": "schema_auto",
        "name": "Auto Schema",
        "version": "1.0.0",
        "fields": [
            {
                "field_id": "title",
                "name": "title",
                "display_name": "Title",
                "type": "string",
                "required": True,
            }
        ],
    }
    template = {
        "template_id": "template_auto",
        "schema_id": "schema_auto",
        "name": "Auto Template",
        "version": "1.0.0",
        "aliases": {"title": ["doc_title"]},
    }
    db.add(Document(
        doc_id="doc_auto",
        title="Auto",
        uir_version="1.0",
        storage_path="documents/doc_auto/uir.json",
        block_count=0,
    ))
    db.add(TargetSchemaRecord(
        schema_id="schema_auto",
        name=schema["name"],
        version=schema["version"],
        schema_json=json.dumps(schema),
        json_schema="{}",
    ))
    db.add(MappingTemplateRecord(
        template_id="template_auto",
        schema_id="schema_auto",
        name=template["name"],
        version=template["version"],
        template_json=json.dumps(template),
    ))
    db.add(ConversionTask(
        task_id="task_auto",
        doc_id="doc_auto",
        schema_id="schema_auto",
        schema_version="1.0.0",
        template_id="template_auto",
        template_version="1.0.0",
        status="created",
        input_hash="sha256:auto",
    ))
    db.commit()
    return "task_auto"


def test_openai_compatible_llm_client_parses_structured_suggestions():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://llm.example.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        payload = json.loads(request.content)
        assert payload["model"] == "schema-map-model"
        assert "approval_unit" in payload["messages"][-1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "suggestions": [
                                    {
                                        "candidate_id": "cand_approval",
                                        "target_field_id": "approval_unit",
                                        "confidence": 0.83,
                                        "reason": "issuer text names the approving unit",
                                    }
                                ]
                            })
                        }
                    }
                ]
            },
        )

    client = LLMClient(
        enabled=True,
        mode="openai_compatible",
        base_url="https://llm.example.test/v1",
        api_key="secret",
        model="schema-map-model",
        prompt_version="prompt-v10",
        transport=httpx.MockTransport(handler),
    )

    suggestions = client.suggest_mappings(
        candidates=[{"candidate_id": "cand_approval", "source_name": "issuer_text"}],
        target_fields=[{"field_id": "approval_unit", "name": "approval_unit"}],
    )

    assert [item.model_dump() for item in suggestions] == [
        {
            "candidate_id": "cand_approval",
            "target_field_id": "approval_unit",
            "confidence": 0.83,
            "reason": "issuer text names the approving unit",
        }
    ]
    assert client.last_audit["status"] == "success"
    assert client.last_audit["mode"] == "openai_compatible"
    assert client.last_audit["model"] == "schema-map-model"
    assert client.last_audit["prompt_version"] == "prompt-v10"
    assert client.last_audit["latency_ms"] >= 0


def test_openai_compatible_llm_client_degrades_to_empty_suggestions_on_failure():
    client = LLMClient(
        enabled=True,
        mode="openai_compatible",
        base_url="https://llm.example.test/v1",
        api_key="secret",
        model="schema-map-model",
        transport=httpx.MockTransport(lambda _request: httpx.Response(503, text="down")),
    )

    assert client.suggest_mappings([{"candidate_id": "cand"}], [{"field_id": "field"}]) == []
    assert client.last_audit["status"] == "failed"
    assert "503" in client.last_audit["error"]


def test_mapping_service_uses_llm_fallback_for_unmapped_targets_and_audits_report(
    mapping_context,
):
    db, storage = mapping_context
    task_id = _seed_unmapped_task(db)

    mappings, report, status = MappingService(
        db,
        storage,
        llm_client=LLMClient(enabled=True, mode="mock"),
    ).run_mapping(task_id, review_threshold=0.8, enable_llm_fallback=True)

    assert status == "review_required"
    assert len(mappings) == 1
    [mapping] = mappings
    assert mapping.method == "llm_fallback"
    assert mapping.candidate_id == "cand_approval"
    assert mapping.target_field_id == "approval_unit"
    assert mapping.need_review is True
    assert "mock suggestion" in mapping.evidence

    stored = db.query(FieldMappingRecord).filter_by(task_id=task_id).one()
    assert stored.method == "llm_fallback"
    assert report.summary["llm_enabled"] is True
    assert report.summary["llm_mode"] == "mock"
    assert report.summary["llm_status"] == "success"
    assert report.summary["llm_suggestion_count"] == 1


def test_mapping_service_keeps_rule_only_report_when_fallback_disabled(mapping_context):
    db, storage = mapping_context
    task_id = _seed_unmapped_task(db)

    mappings, report, status = MappingService(db, storage).run_mapping(
        task_id,
        review_threshold=0.8,
        enable_llm_fallback=False,
    )

    assert mappings == []
    assert status == "mapping_completed"
    assert report.summary["llm_enabled"] is False
    assert report.summary["llm_suggestion_count"] == 0


def test_mapping_service_generates_candidates_when_missing(mapping_context):
    db, storage = mapping_context
    task_id = _seed_autogenerate_task(db, storage)

    mappings, report, status = MappingService(db, storage).run_mapping(
        task_id,
        review_threshold=0.8,
        enable_llm_fallback=False,
    )

    assert status == "mapping_completed"
    assert len(mappings) == 1
    assert mappings[0].target_field_id == "title"
    assert report.summary["mapped_fields"] == 1
    assert db.query(FieldCandidateRecord).filter_by(task_id=task_id).count() >= 1


def test_mapping_service_raises_for_missing_schema_or_template(mapping_context):
    db, storage = mapping_context
    db.add(Document(
        doc_id="doc_missing_refs",
        title="Missing",
        uir_version="1.0",
        storage_path="documents/missing/uir.json",
        block_count=0,
    ))
    db.add(ConversionTask(
        task_id="task_missing_schema",
        doc_id="doc_missing_refs",
        schema_id="missing_schema",
        schema_version="1.0.0",
        template_id="missing_template",
        template_version="1.0.0",
        status="created",
        input_hash="sha256:missing",
    ))
    schema = {
        "schema_id": "schema_exists",
        "name": "Schema Exists",
        "version": "1.0.0",
        "fields": [
            {
                "field_id": "title",
                "name": "title",
                "display_name": "Title",
                "type": "string",
            }
        ],
    }
    db.add(TargetSchemaRecord(
        schema_id="schema_exists",
        name=schema["name"],
        version=schema["version"],
        schema_json=json.dumps(schema),
        json_schema="{}",
    ))
    db.add(ConversionTask(
        task_id="task_missing_template",
        doc_id="doc_missing_refs",
        schema_id="schema_exists",
        schema_version="1.0.0",
        template_id="missing_template",
        template_version="1.0.0",
        status="created",
        input_hash="sha256:missing",
    ))
    for task_id in ("task_missing_schema", "task_missing_template"):
        db.add(FieldCandidateRecord(
            candidate_id=f"cand_{task_id}",
            task_id=task_id,
            doc_id="doc_missing_refs",
            source_path="metadata.title",
            source_name="title",
            display_name="Title",
            value_sample=json.dumps("Missing"),
            inferred_type="string",
            source_blocks_json="[]",
            confidence=0.95,
        ))
    db.commit()

    with pytest.raises(LookupError, match="schema not found"):
        MappingService(db, storage).run_mapping("task_missing_schema", 0.8)
    with pytest.raises(LookupError, match="template not found"):
        MappingService(db, storage).run_mapping("task_missing_template", 0.8)


def test_mapping_service_skips_duplicate_or_invalid_llm_suggestions(mapping_context):
    db, storage = mapping_context
    schema = {
        "schema_id": "schema_skip",
        "name": "Skip Schema",
        "version": "1.0.0",
        "fields": [
            {
                "field_id": "title",
                "name": "title",
                "display_name": "Title",
                "type": "string",
                "required": True,
            },
            {
                "field_id": "owner",
                "name": "owner",
                "display_name": "Owner",
                "type": "string",
                "required": True,
            },
        ],
    }
    template = {
        "template_id": "template_skip",
        "schema_id": "schema_skip",
        "name": "Skip Template",
        "version": "1.0.0",
        "aliases": {"title": ["doc_title"]},
    }
    db.add(Document(
        doc_id="doc_skip",
        title="Skip",
        uir_version="1.0",
        storage_path="documents/doc_skip/uir.json",
        block_count=0,
    ))
    db.add(TargetSchemaRecord(
        schema_id="schema_skip",
        name=schema["name"],
        version=schema["version"],
        schema_json=json.dumps(schema),
        json_schema="{}",
    ))
    db.add(MappingTemplateRecord(
        template_id="template_skip",
        schema_id="schema_skip",
        name=template["name"],
        version=template["version"],
        template_json=json.dumps(template),
    ))
    db.add(ConversionTask(
        task_id="task_skip",
        doc_id="doc_skip",
        schema_id="schema_skip",
        schema_version="1.0.0",
        template_id="template_skip",
        template_version="1.0.0",
        status="candidates_ready",
        input_hash="sha256:skip",
    ))
    for candidate_id, source_name in (
        ("cand_skip_title", "doc_title"),
        ("cand_skip_owner", "zzzzzzzz"),
    ):
        db.add(FieldCandidateRecord(
            candidate_id=candidate_id,
            task_id="task_skip",
            doc_id="doc_skip",
            source_path=f"metadata.{source_name}",
            source_name=source_name,
            display_name=source_name,
            value_sample=json.dumps(source_name),
            inferred_type="string",
            source_blocks_json="[]",
            confidence=0.95,
        ))
    db.commit()

    class InvalidSuggestionClient:
        mode = "mock"
        model = "fake"
        prompt_version = "test"
        last_audit = {
            "enabled": True,
            "mode": "mock",
            "model": "fake",
            "prompt_version": "test",
            "status": "success",
            "suggestion_count": 2,
            "latency_ms": 0,
            "error": None,
        }

        def suggest_mappings(self, candidates, target_fields):
            return [
                LLMSuggestion(
                    candidate_id="cand_skip_owner",
                    target_field_id="title",
                    confidence=0.9,
                    reason="duplicate target",
                ),
                LLMSuggestion(
                    candidate_id="missing_candidate",
                    target_field_id="owner",
                    confidence=0.9,
                    reason="invalid candidate",
                ),
            ]

    mappings, report, status = MappingService(
        db,
        storage,
        llm_client=InvalidSuggestionClient(),
    ).run_mapping("task_skip", review_threshold=0.8, enable_llm_fallback=True)

    assert status == "mapping_completed"
    assert [mapping.target_field_id for mapping in mappings] == ["title"]
    assert report.summary["llm_suggestion_count"] == 2
