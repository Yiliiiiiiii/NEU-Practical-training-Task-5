import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
    KnowledgePackItemRecord,
    KnowledgePackRecord,
    LearningCandidateRecord,
    MappingTemplateRecord,
    RealRunRecord,
    ReviewRecord,
    TargetSchemaRecord,
    TransformTraceRecord,
)
from app.schemas.knowledge import (
    CandidateDecisionRequest,
    KnowledgePackCreateRequest,
    LearningCandidateView,
    RealRunView,
)
from app.services.knowledge_service import KnowledgeService
from app.services.storage_service import StorageService


def test_knowledge_schema_models_parse_minimal_payloads():
    run = RealRunView(
        real_run_id="run_1",
        task_id="task_1",
        doc_id="doc_1",
        schema_id="schema_1",
        template_id="template_1",
        input_hash="sha256:abc",
        status="captured",
        summary={"mapped_fields": 2},
        report_paths={"mapping_report": "tasks/task_1/mapping_report.json"},
    )
    candidate = LearningCandidateView(
        candidate_id="lc_1",
        real_run_id="run_1",
        task_id="task_1",
        candidate_type="alias_candidate",
        status="pending",
        risk_level="medium",
        target_field_id="title",
        proposed_payload={"aliases": ["doc_title"]},
        evidence={"source_name": "doc_title"},
        generator="review_feedback",
        confidence=0.95,
    )
    decision = CandidateDecisionRequest(
        decision="approved",
        reviewer="tester",
        final_payload={"aliases": ["doc_title"]},
        reason="reviewed source field maps to title",
    )
    pack_request = KnowledgePackCreateRequest(
        name="policy title aliases",
        scope={"schema_id": "schema_1", "template_id": "template_1"},
        candidate_ids=["lc_1"],
        reviewer="tester",
    )

    assert run.summary["mapped_fields"] == 2
    assert candidate.status == "pending"
    assert decision.decision == "approved"
    assert pack_request.candidate_ids == ["lc_1"]


def test_knowledge_database_records_store_json_strings():
    run = RealRunRecord(
        real_run_id="run_1",
        task_id="task_1",
        doc_id="doc_1",
        schema_id="schema_1",
        template_id="template_1",
        input_hash="sha256:abc",
        status="captured",
        summary_json=json.dumps({"review_required": 1}),
        report_paths_json=json.dumps({"mapping_report": "tasks/task_1/mapping_report.json"}),
    )
    candidate = LearningCandidateRecord(
        candidate_id="lc_1",
        real_run_id="run_1",
        task_id="task_1",
        candidate_type="alias_candidate",
        status="pending",
        risk_level="medium",
        target_field_id="title",
        proposed_payload_json=json.dumps({"aliases": ["doc_title"]}),
        final_payload_json="{}",
        evidence_json=json.dumps({"source_name": "doc_title"}),
        generator="review_feedback",
        confidence=0.95,
    )
    pack = KnowledgePackRecord(
        pack_id="kp_1",
        name="policy aliases",
        scope_json=json.dumps({"schema_id": "schema_1"}),
        status="draft",
        version="1.0.0",
        item_count=1,
        regression_report_path=None,
        reviewer="tester",
    )
    item = KnowledgePackItemRecord(
        item_id="kpi_1",
        pack_id="kp_1",
        item_type="alias_candidate",
        target_field_id="title",
        payload_json=json.dumps({"aliases": ["doc_title"]}),
        source_candidate_id="lc_1",
    )

    assert json.loads(run.summary_json)["review_required"] == 1
    assert json.loads(candidate.proposed_payload_json)["aliases"] == ["doc_title"]
    assert json.loads(pack.scope_json)["schema_id"] == "schema_1"
    assert item.target_field_id == "title"


@pytest.fixture()
def knowledge_context(tmp_path):
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


def _seed_reviewed_task(db, storage: StorageService) -> str:
    schema = {
        "schema_id": "schema_k",
        "name": "Knowledge Schema",
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
        "json_schema": {
            "type": "object",
            "required": ["title", "owner"],
            "properties": {
                "title": {"type": "string"},
                "owner": {"type": "string"},
            },
        },
    }
    template = {
        "template_id": "template_k",
        "schema_id": "schema_k",
        "name": "Knowledge Template",
        "version": "1.0.0",
        "aliases": {},
        "regex_rules": [],
        "transform_rules": [],
        "defaults": {},
        "enum_maps": {},
    }
    db.add(Document(
        doc_id="doc_k",
        title="Doc K",
        uir_version="1.0",
        storage_path="documents/doc_k/uir.json",
        block_count=0,
    ))
    db.add(TargetSchemaRecord(
        schema_id="schema_k",
        name="Knowledge Schema",
        version="1.0.0",
        schema_json=json.dumps(schema),
        json_schema=json.dumps(schema["json_schema"]),
    ))
    db.add(MappingTemplateRecord(
        template_id="template_k",
        schema_id="schema_k",
        name="Knowledge Template",
        version="1.0.0",
        template_json=json.dumps(template),
    ))
    db.add(ConversionTask(
        task_id="task_k",
        doc_id="doc_k",
        schema_id="schema_k",
        schema_version="1.0.0",
        template_id="template_k",
        template_version="1.0.0",
        status="mapping_completed",
        input_hash="sha256:knowledge",
        options_json="{}",
    ))
    db.add(FieldCandidateRecord(
        candidate_id="cand_title",
        task_id="task_k",
        doc_id="doc_k",
        source_path="metadata.doc_title",
        source_name="doc_title",
        display_name="Document Title",
        value_sample=json.dumps("A title"),
        inferred_type="string",
        source_blocks_json="[]",
        confidence=0.95,
    ))
    db.add(FieldMappingRecord(
        mapping_id="map_title",
        task_id="task_k",
        candidate_id="cand_title",
        target_field_id="title",
        method="llm_fallback",
        confidence=0.83,
        status="confirmed",
        need_review=False,
        evidence_json=json.dumps(["review confirmed"]),
    ))
    db.add(ReviewRecord(
        review_id="rev_title",
        task_id="task_k",
        mapping_id="map_title",
        old_target_field_id="owner",
        new_target_field_id="title",
        decision="changed",
        comment="doc_title is the document title",
        reviewer="tester",
    ))
    db.add(TransformTraceRecord(
        trace_id="trace_bad",
        task_id="task_k",
        stage="field_transform",
        action="type_cast",
        target_field_id="owner",
        before_json="{}",
        after_json="{}",
        rule_id="cast_owner",
        reason="cannot cast owner",
        status="error",
    ))
    storage.save_json(
        "tasks/task_k/mapping_report.json",
        {
            "task_id": "task_k",
            "schema_id": "schema_k",
            "summary": {
                "mapped_fields": 1,
                "review_required": 0,
                "llm_status": "success",
            },
            "mappings": [],
            "unmapped": ["owner"],
            "review_required_items": [],
        },
    )
    db.commit()
    return "task_k"


def test_capture_real_run_records_reports_and_task_context(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)

    run = KnowledgeService(db, storage).capture_real_run(task_id)

    assert run.task_id == task_id
    assert run.schema_id == "schema_k"
    assert run.summary["mapped_fields"] == 1
    assert run.report_paths["mapping_report"] == "tasks/task_k/mapping_report.json"


def test_derive_learning_candidates_from_review_llm_unmapped_and_trace(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)
    service = KnowledgeService(db, storage)
    run = service.capture_real_run(task_id)

    candidates = service.derive_learning_candidates(run.real_run_id)
    by_type = {candidate.candidate_type: candidate for candidate in candidates}

    assert by_type["alias_candidate"].target_field_id == "title"
    assert by_type["alias_candidate"].proposed_payload == {"aliases": ["doc_title"]}
    assert by_type["badcase_candidate"].evidence["unmapped_required_fields"] == ["owner"]
    assert any(candidate.generator == "transform_trace" for candidate in candidates)
