import json

from app.db.models import (
    KnowledgePackItemRecord,
    KnowledgePackRecord,
    LearningCandidateRecord,
    RealRunRecord,
)
from app.schemas.knowledge import (
    CandidateDecisionRequest,
    KnowledgePackCreateRequest,
    LearningCandidateView,
    RealRunView,
)


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
