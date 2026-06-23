# Mapping Knowledge Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a controlled topic 5 growth loop that turns reviewed mapping evidence into versioned mapping knowledge packs and human-reviewed evaluation assets.

**Architecture:** Add knowledge-specific database records, Pydantic contracts, backend services, and a thin API router. Integrate active knowledge packs by resolving an effective Mapping Template before deterministic mapping runs, while leaving LLM output pending until human approval. Add a compact frontend Knowledge page for review, approval, activation, and metrics.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Pydantic v2, SQLite, pytest, React, TypeScript, Vitest.

---

## File Structure

- Create `backend/app/schemas/knowledge.py`: API/data contracts for real runs, learning candidates, candidate decisions, knowledge packs, and metrics.
- Modify `backend/app/db/models.py`: add `RealRunRecord`, `LearningCandidateRecord`, `KnowledgePackRecord`, and `KnowledgePackItemRecord`.
- Create `backend/app/services/knowledge_service.py`: capture real runs, derive candidates, decide candidates, create/activate packs, produce metrics, and export sanitized fixtures.
- Create `backend/app/services/effective_template_service.py`: merge active knowledge packs into a selected Mapping Template.
- Modify `backend/app/services/mapping_service.py`: resolve the effective template before mapping and include knowledge pack IDs in the mapping report summary.
- Create `backend/app/api/v1/knowledge.py`: expose knowledge review and pack APIs.
- Modify `backend/app/api/v1/router.py`: include the knowledge router.
- Modify `backend/tests/test_api_contract_matrix.py`: include new knowledge endpoints in the expected route inventory.
- Create `backend/tests/test_mapping_knowledge.py`: service and API tests for the growth loop.
- Create `backend/tests/test_effective_template_service.py`: focused merge/resolution tests.
- Modify `frontend/src/api/types.ts`: add knowledge API types.
- Modify `frontend/src/api/client.ts`: add knowledge API client methods.
- Modify `frontend/src/appTypes.ts`, `frontend/src/navItems.ts`, and `frontend/src/App.tsx`: add the `knowledge` view.
- Create `frontend/src/pages/KnowledgePage.tsx`: review queue, pack activation, and metrics.
- Create `frontend/src/__tests__/knowledgePage.test.tsx`: frontend behavior tests.
- Modify `docs/openapi.json` and `README.md`: document new endpoints and topic 5 boundaries after implementation.

## Task 1: Knowledge Data Contracts And Persistence

**Files:**
- Create: `backend/app/schemas/knowledge.py`
- Modify: `backend/app/db/models.py`
- Test: `backend/tests/test_mapping_knowledge.py`

- [ ] **Step 1: Write failing schema/model tests**

Add these tests to `backend/tests/test_mapping_knowledge.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py -q
```

Expected: FAIL with import errors for `app.schemas.knowledge` and missing database record classes.

- [ ] **Step 3: Add Pydantic knowledge schemas**

Create `backend/app/schemas/knowledge.py`:

```python
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel


CandidateType = Literal[
    "alias_candidate",
    "regex_candidate",
    "enum_map_candidate",
    "default_candidate",
    "transform_candidate",
    "gold_mapping_candidate",
    "badcase_candidate",
]
CandidateStatus = Literal["pending", "approved", "rejected", "superseded"]
CandidateDecision = Literal["approved", "rejected"]
KnowledgePackStatus = Literal["draft", "active", "superseded"]


class RealRunView(StrictBaseModel):
    real_run_id: str
    task_id: str
    doc_id: str
    schema_id: str
    template_id: str
    input_hash: str
    status: str
    summary: dict[str, Any] = Field(default_factory=dict)
    report_paths: dict[str, str] = Field(default_factory=dict)


class LearningCandidateView(StrictBaseModel):
    candidate_id: str
    real_run_id: str
    task_id: str
    candidate_type: CandidateType
    status: CandidateStatus
    risk_level: Literal["low", "medium", "high"]
    target_field_id: str | None = None
    proposed_payload: dict[str, Any] = Field(default_factory=dict)
    final_payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    generator: str
    confidence: float


class CandidateDecisionRequest(StrictBaseModel):
    decision: CandidateDecision
    reviewer: str = "human"
    final_payload: dict[str, Any] = Field(default_factory=dict)
    reason: str


class CandidateListResponse(StrictBaseModel):
    items: list[LearningCandidateView]


class KnowledgePackCreateRequest(StrictBaseModel):
    name: str
    scope: dict[str, str] = Field(default_factory=dict)
    candidate_ids: list[str]
    reviewer: str = "human"


class KnowledgePackView(StrictBaseModel):
    pack_id: str
    name: str
    scope: dict[str, str] = Field(default_factory=dict)
    status: KnowledgePackStatus
    version: str
    item_count: int
    regression_report_path: str | None = None
    reviewer: str


class KnowledgePackListResponse(StrictBaseModel):
    items: list[KnowledgePackView]


class KnowledgeMetricsResponse(StrictBaseModel):
    real_runs: int
    pending_candidates: int
    approved_candidates: int
    rejected_candidates: int
    active_packs: int
```

- [ ] **Step 4: Add SQLAlchemy records**

Modify `backend/app/db/models.py` after `ReviewRecord`:

```python

class RealRunRecord(Base):
    __tablename__ = "real_runs"

    real_run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    doc_id: Mapped[str] = mapped_column(Text)
    schema_id: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(Text)
    input_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    report_paths_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningCandidateRecord(Base):
    __tablename__ = "learning_candidates"

    candidate_id: Mapped[str] = mapped_column(Text, primary_key=True)
    real_run_id: Mapped[str] = mapped_column(Text, ForeignKey("real_runs.real_run_id"))
    task_id: Mapped[str] = mapped_column(Text, ForeignKey("conversion_tasks.task_id"))
    candidate_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")
    risk_level: Mapped[str] = mapped_column(Text)
    target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    final_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    generator: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgePackRecord(Base):
    __tablename__ = "knowledge_packs"

    pack_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    scope_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(Text, default="draft")
    version: Mapped[str] = mapped_column(Text)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    regression_report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class KnowledgePackItemRecord(Base):
    __tablename__ = "knowledge_pack_items"

    item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    pack_id: Mapped[str] = mapped_column(Text, ForeignKey("knowledge_packs.pack_id"))
    item_type: Mapped[str] = mapped_column(Text)
    target_field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    source_candidate_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("learning_candidates.candidate_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py -q
```

Expected: PASS for the two new tests.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/schemas/knowledge.py backend/app/db/models.py backend/tests/test_mapping_knowledge.py
git commit -m "feat: add knowledge growth data contracts"
```

## Task 2: Capture Real Runs And Derive Learning Candidates

**Files:**
- Create: `backend/app/services/knowledge_service.py`
- Modify: `backend/tests/test_mapping_knowledge.py`

- [ ] **Step 1: Write failing service tests**

Append to `backend/tests/test_mapping_knowledge.py`:

```python
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
    MappingTemplateRecord,
    ReviewRecord,
    TargetSchemaRecord,
    TransformTraceRecord,
)
from app.services.knowledge_service import KnowledgeService
from app.services.storage_service import StorageService


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.knowledge_service'`.

- [ ] **Step 3: Implement real-run capture and candidate derivation**

Create `backend/app/services/knowledge_service.py`:

```python
import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    ConversionTask,
    FieldCandidateRecord,
    FieldMappingRecord,
    KnowledgePackItemRecord,
    KnowledgePackRecord,
    LearningCandidateRecord,
    RealRunRecord,
    ReviewRecord,
    TransformTraceRecord,
    utcnow,
)
from app.schemas.knowledge import (
    CandidateDecisionRequest,
    KnowledgeMetricsResponse,
    KnowledgePackCreateRequest,
    KnowledgePackView,
    LearningCandidateView,
    RealRunView,
)
from app.services.storage_service import StorageService
from app.utils.ids import new_id


class KnowledgeValidationError(ValueError):
    pass


class KnowledgeService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def capture_real_run(self, task_id: str) -> RealRunView:
        task = self._task(task_id)
        mapping_path = f"tasks/{task_id}/mapping_report.json"
        try:
            mapping_report = self.storage.read_json(mapping_path)
        except FileNotFoundError:
            mapping_report = {"summary": {}, "unmapped": []}
        summary = dict(mapping_report.get("summary", {}))
        report_paths = {"mapping_report": mapping_path}
        record = RealRunRecord(
            real_run_id=new_id("run"),
            task_id=task.task_id,
            doc_id=task.doc_id,
            schema_id=task.schema_id,
            template_id=task.template_id,
            input_hash=task.input_hash,
            status="captured",
            summary_json=json.dumps(summary, ensure_ascii=False, sort_keys=True),
            report_paths_json=json.dumps(report_paths, ensure_ascii=False, sort_keys=True),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._real_run_view(record)

    def derive_learning_candidates(self, real_run_id: str) -> list[LearningCandidateView]:
        run = self._real_run(real_run_id)
        created: list[LearningCandidateRecord] = []
        created.extend(self._review_alias_candidates(run))
        created.extend(self._unmapped_badcase_candidates(run))
        created.extend(self._trace_badcase_candidates(run))
        for record in created:
            self.db.add(record)
        self.db.commit()
        return [self._candidate_view(record) for record in created]

    def _review_alias_candidates(self, run: RealRunRecord) -> list[LearningCandidateRecord]:
        candidates: list[LearningCandidateRecord] = []
        reviews = (
            self.db.query(ReviewRecord)
            .filter(ReviewRecord.task_id == run.task_id)
            .order_by(ReviewRecord.created_at.asc())
            .all()
        )
        for review in reviews:
            mapping = self.db.get(FieldMappingRecord, review.mapping_id)
            if mapping is None or mapping.task_id != run.task_id:
                continue
            source = self.db.get(FieldCandidateRecord, mapping.candidate_id)
            if source is None:
                continue
            target = review.new_target_field_id or mapping.target_field_id
            if not target or not source.source_name:
                continue
            generator = "llm_review_feedback" if mapping.method == "llm_fallback" else "review_feedback"
            candidates.append(self._candidate_record(
                run=run,
                candidate_type="alias_candidate",
                target_field_id=target,
                proposed_payload={"aliases": [source.source_name]},
                evidence={
                    "mapping_id": mapping.mapping_id,
                    "source_name": source.source_name,
                    "source_path": source.source_path,
                    "old_target_field_id": review.old_target_field_id,
                    "new_target_field_id": target,
                    "review_decision": review.decision,
                },
                generator=generator,
                confidence=mapping.confidence,
                risk_level="high" if mapping.method == "llm_fallback" else "medium",
            ))
        return candidates

    def _unmapped_badcase_candidates(self, run: RealRunRecord) -> list[LearningCandidateRecord]:
        paths = json.loads(run.report_paths_json or "{}")
        mapping_path = paths.get("mapping_report")
        if not mapping_path:
            return []
        try:
            report = self.storage.read_json(mapping_path)
        except FileNotFoundError:
            return []
        unmapped = [str(item) for item in report.get("unmapped", [])]
        if not unmapped:
            return []
        return [self._candidate_record(
            run=run,
            candidate_type="badcase_candidate",
            target_field_id=None,
            proposed_payload={"case_type": "unmapped_required"},
            evidence={"unmapped_required_fields": unmapped},
            generator="mapping_report",
            confidence=1.0,
            risk_level="high",
        )]

    def _trace_badcase_candidates(self, run: RealRunRecord) -> list[LearningCandidateRecord]:
        traces = (
            self.db.query(TransformTraceRecord)
            .filter(
                TransformTraceRecord.task_id == run.task_id,
                TransformTraceRecord.status == "error",
            )
            .all()
        )
        return [
            self._candidate_record(
                run=run,
                candidate_type="badcase_candidate",
                target_field_id=trace.target_field_id,
                proposed_payload={"case_type": "transform_error"},
                evidence={
                    "trace_id": trace.trace_id,
                    "action": trace.action,
                    "rule_id": trace.rule_id,
                    "reason": trace.reason,
                },
                generator="transform_trace",
                confidence=1.0,
                risk_level="high",
            )
            for trace in traces
        ]

    def _candidate_record(
        self,
        *,
        run: RealRunRecord,
        candidate_type: str,
        target_field_id: str | None,
        proposed_payload: dict[str, Any],
        evidence: dict[str, Any],
        generator: str,
        confidence: float,
        risk_level: str,
    ) -> LearningCandidateRecord:
        return LearningCandidateRecord(
            candidate_id=new_id("lc"),
            real_run_id=run.real_run_id,
            task_id=run.task_id,
            candidate_type=candidate_type,
            status="pending",
            risk_level=risk_level,
            target_field_id=target_field_id,
            proposed_payload_json=json.dumps(proposed_payload, ensure_ascii=False, sort_keys=True),
            final_payload_json="{}",
            evidence_json=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            generator=generator,
            confidence=confidence,
        )

    def _task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task

    def _real_run(self, real_run_id: str) -> RealRunRecord:
        run = self.db.get(RealRunRecord, real_run_id)
        if run is None:
            raise LookupError("real run not found")
        return run

    @staticmethod
    def _real_run_view(record: RealRunRecord) -> RealRunView:
        return RealRunView(
            real_run_id=record.real_run_id,
            task_id=record.task_id,
            doc_id=record.doc_id,
            schema_id=record.schema_id,
            template_id=record.template_id,
            input_hash=record.input_hash,
            status=record.status,
            summary=json.loads(record.summary_json or "{}"),
            report_paths=json.loads(record.report_paths_json or "{}"),
        )

    @staticmethod
    def _candidate_view(record: LearningCandidateRecord) -> LearningCandidateView:
        return LearningCandidateView(
            candidate_id=record.candidate_id,
            real_run_id=record.real_run_id,
            task_id=record.task_id,
            candidate_type=record.candidate_type,
            status=record.status,
            risk_level=record.risk_level,
            target_field_id=record.target_field_id,
            proposed_payload=json.loads(record.proposed_payload_json or "{}"),
            final_payload=json.loads(record.final_payload_json or "{}"),
            evidence=json.loads(record.evidence_json or "{}"),
            generator=record.generator,
            confidence=record.confidence,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py -q
```

Expected: PASS for schema/model and derivation tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/knowledge_service.py backend/tests/test_mapping_knowledge.py
git commit -m "feat: derive mapping learning candidates"
```

## Task 3: Candidate Decisions And Knowledge Pack Publishing

**Files:**
- Modify: `backend/app/services/knowledge_service.py`
- Modify: `backend/tests/test_mapping_knowledge.py`

- [ ] **Step 1: Write failing approval and pack tests**

Append to `backend/tests/test_mapping_knowledge.py`:

```python
from app.schemas.knowledge import CandidateDecisionRequest, KnowledgePackCreateRequest


def test_pending_candidates_do_not_create_pack_until_approved(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)
    service = KnowledgeService(db, storage)
    run = service.capture_real_run(task_id)
    [candidate, *_] = service.derive_learning_candidates(run.real_run_id)

    with pytest.raises(ValueError, match="candidate must be approved"):
        service.create_knowledge_pack(KnowledgePackCreateRequest(
            name="Title aliases",
            scope={"schema_id": "schema_k", "template_id": "template_k"},
            candidate_ids=[candidate.candidate_id],
            reviewer="tester",
        ))


def test_approved_alias_candidate_creates_draft_pack_items(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)
    service = KnowledgeService(db, storage)
    run = service.capture_real_run(task_id)
    candidate = next(
        item for item in service.derive_learning_candidates(run.real_run_id)
        if item.candidate_type == "alias_candidate"
    )

    decided = service.decide_candidate(
        candidate.candidate_id,
        CandidateDecisionRequest(
            decision="approved",
            reviewer="tester",
            final_payload={"aliases": ["doc_title"]},
            reason="confirmed by review",
        ),
    )
    pack = service.create_knowledge_pack(KnowledgePackCreateRequest(
        name="Title aliases",
        scope={"schema_id": "schema_k", "template_id": "template_k"},
        candidate_ids=[candidate.candidate_id],
        reviewer="tester",
    ))

    assert decided.status == "approved"
    assert pack.status == "draft"
    assert pack.item_count == 1
    assert pack.scope["template_id"] == "template_k"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py::test_pending_candidates_do_not_create_pack_until_approved tests/test_mapping_knowledge.py::test_approved_alias_candidate_creates_draft_pack_items -q
```

Expected: FAIL with missing `decide_candidate` and `create_knowledge_pack`.

- [ ] **Step 3: Implement candidate decisions and pack creation**

Add these methods to `KnowledgeService` in `backend/app/services/knowledge_service.py`:

```python
    def decide_candidate(
        self,
        candidate_id: str,
        request: CandidateDecisionRequest,
    ) -> LearningCandidateView:
        record = self._candidate(candidate_id)
        record.status = request.decision
        record.reviewer = request.reviewer
        record.decision_reason = request.reason
        if request.decision == "approved":
            final_payload = request.final_payload or json.loads(record.proposed_payload_json or "{}")
            record.final_payload_json = json.dumps(
                final_payload,
                ensure_ascii=False,
                sort_keys=True,
            )
        else:
            record.final_payload_json = "{}"
        self.db.commit()
        self.db.refresh(record)
        return self._candidate_view(record)

    def create_knowledge_pack(
        self,
        request: KnowledgePackCreateRequest,
    ) -> KnowledgePackView:
        if not request.candidate_ids:
            raise KnowledgeValidationError("candidate_ids must not be empty")
        records = [self._candidate(candidate_id) for candidate_id in request.candidate_ids]
        for record in records:
            if record.status != "approved":
                raise KnowledgeValidationError("candidate must be approved before publishing")
        pack = KnowledgePackRecord(
            pack_id=new_id("kp"),
            name=request.name,
            scope_json=json.dumps(request.scope, ensure_ascii=False, sort_keys=True),
            status="draft",
            version="1.0.0",
            item_count=len(records),
            regression_report_path=None,
            reviewer=request.reviewer,
        )
        self.db.add(pack)
        self.db.flush()
        for record in records:
            payload = json.loads(record.final_payload_json or "{}")
            self.db.add(KnowledgePackItemRecord(
                item_id=new_id("kpi"),
                pack_id=pack.pack_id,
                item_type=record.candidate_type,
                target_field_id=record.target_field_id,
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                source_candidate_id=record.candidate_id,
            ))
        self.db.commit()
        self.db.refresh(pack)
        return self._pack_view(pack)

    def _candidate(self, candidate_id: str) -> LearningCandidateRecord:
        record = self.db.get(LearningCandidateRecord, candidate_id)
        if record is None:
            raise LookupError("learning candidate not found")
        return record

    @staticmethod
    def _pack_view(record: KnowledgePackRecord) -> KnowledgePackView:
        return KnowledgePackView(
            pack_id=record.pack_id,
            name=record.name,
            scope=json.loads(record.scope_json or "{}"),
            status=record.status,
            version=record.version,
            item_count=record.item_count,
            regression_report_path=record.regression_report_path,
            reviewer=record.reviewer,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py -q
```

Expected: PASS for all knowledge service tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/knowledge_service.py backend/tests/test_mapping_knowledge.py
git commit -m "feat: approve learning candidates into knowledge packs"
```

## Task 4: Effective Template Resolution

**Files:**
- Create: `backend/app/services/effective_template_service.py`
- Create: `backend/tests/test_effective_template_service.py`

- [ ] **Step 1: Write failing effective-template tests**

Create `backend/tests/test_effective_template_service.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_effective_template_service.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `effective_template_service`.

- [ ] **Step 3: Implement effective-template merging**

Create `backend/app/services/effective_template_service.py`:

```python
import json

from sqlalchemy.orm import Session

from app.db.models import KnowledgePackItemRecord, KnowledgePackRecord
from app.schemas.mapping_template import MappingTemplate, RegexRule
from app.schemas.transform import TransformRule


class EffectiveTemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(self, template: MappingTemplate) -> tuple[MappingTemplate, list[str]]:
        data = template.model_dump(mode="json")
        pack_ids: list[str] = []
        packs = (
            self.db.query(KnowledgePackRecord)
            .filter(KnowledgePackRecord.status == "active")
            .order_by(KnowledgePackRecord.created_at.asc())
            .all()
        )
        for pack in packs:
            scope = json.loads(pack.scope_json or "{}")
            if not self._scope_matches(scope, template):
                continue
            pack_ids.append(pack.pack_id)
            items = (
                self.db.query(KnowledgePackItemRecord)
                .filter(KnowledgePackItemRecord.pack_id == pack.pack_id)
                .order_by(KnowledgePackItemRecord.created_at.asc())
                .all()
            )
            for item in items:
                payload = json.loads(item.payload_json or "{}")
                if item.item_type == "alias_candidate" and item.target_field_id:
                    aliases = data.setdefault("aliases", {}).setdefault(item.target_field_id, [])
                    for alias in payload.get("aliases", []):
                        if alias not in aliases:
                            aliases.append(alias)
                elif item.item_type == "regex_candidate":
                    data.setdefault("regex_rules", []).append(payload)
                elif item.item_type == "enum_map_candidate" and item.target_field_id:
                    data.setdefault("enum_maps", {})[item.target_field_id] = payload.get("map", {})
                elif item.item_type == "default_candidate" and item.target_field_id:
                    data.setdefault("defaults", {})[item.target_field_id] = payload.get("value")
                elif item.item_type == "transform_candidate":
                    data.setdefault("transform_rules", []).append(payload)
        resolved = MappingTemplate(
            **{
                **data,
                "regex_rules": [RegexRule.model_validate(rule) for rule in data.get("regex_rules", [])],
                "transform_rules": [
                    TransformRule.model_validate(rule)
                    for rule in data.get("transform_rules", [])
                ],
            }
        )
        return resolved, pack_ids

    @staticmethod
    def _scope_matches(scope: dict, template: MappingTemplate) -> bool:
        schema_id = scope.get("schema_id")
        template_id = scope.get("template_id")
        if template_id and template_id != template.template_id:
            return False
        if schema_id and schema_id != template.schema_id:
            return False
        return bool(schema_id or template_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_effective_template_service.py -q
```

Expected: PASS for both effective-template tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/effective_template_service.py backend/tests/test_effective_template_service.py
git commit -m "feat: resolve active mapping knowledge packs"
```

## Task 5: Integrate Knowledge Packs Into Mapping Runs

**Files:**
- Modify: `backend/app/services/mapping_service.py`
- Modify: `backend/tests/test_mapping_knowledge.py`

- [ ] **Step 1: Write failing mapping integration test**

Append to `backend/tests/test_mapping_knowledge.py`:

```python
from app.db.models import KnowledgePackItemRecord, KnowledgePackRecord
from app.services.mapping_service import MappingService


def test_active_knowledge_pack_affects_future_mapping_and_report(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)
    db.query(FieldMappingRecord).delete()
    db.query(ReviewRecord).delete()
    db.add(KnowledgePackRecord(
        pack_id="kp_active_title",
        name="Active title aliases",
        scope_json=json.dumps({"schema_id": "schema_k", "template_id": "template_k"}),
        status="active",
        version="1.0.0",
        item_count=1,
        reviewer="tester",
    ))
    db.add(KnowledgePackItemRecord(
        item_id="kpi_active_title",
        pack_id="kp_active_title",
        item_type="alias_candidate",
        target_field_id="title",
        payload_json=json.dumps({"aliases": ["doc_title"]}),
        source_candidate_id=None,
    ))
    db.commit()

    mappings, report, status = MappingService(db, storage).run_mapping(
        task_id,
        review_threshold=0.8,
        enable_llm_fallback=False,
    )

    assert status == "mapping_completed"
    assert mappings[0].method == "alias_match"
    assert mappings[0].target_field_id == "title"
    assert report.summary["knowledge_pack_ids"] == ["kp_active_title"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py::test_active_knowledge_pack_affects_future_mapping_and_report -q
```

Expected: FAIL because `knowledge_pack_ids` is absent and active pack aliases are not used.

- [ ] **Step 3: Resolve effective template in MappingService**

Modify `backend/app/services/mapping_service.py`:

```python
from app.services.effective_template_service import EffectiveTemplateService
```

In `run_mapping`, replace:

```python
        template = self._load_template(task.template_id)
```

with:

```python
        template = self._load_template(task.template_id)
        template, knowledge_pack_ids = EffectiveTemplateService(self.db).resolve(template)
```

Change `_build_report` call from:

```python
        report = self._build_report(task_id, schema, mappings, llm_audit)
```

to:

```python
        report = self._build_report(task_id, schema, mappings, llm_audit, knowledge_pack_ids)
```

Change `_build_report` signature:

```python
    def _build_report(
        self,
        task_id: str,
        schema: TargetSchema,
        mappings: list[FieldMapping],
        llm_audit: dict,
        knowledge_pack_ids: list[str],
    ) -> MappingReport:
```

Add this key to `summary`:

```python
                "knowledge_pack_ids": knowledge_pack_ids,
```

- [ ] **Step 4: Run integration tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py tests/test_phase10_llm_fallback.py -q
```

Expected: PASS. Existing LLM fallback report tests must continue to pass because `knowledge_pack_ids` defaults to an empty list.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/mapping_service.py backend/tests/test_mapping_knowledge.py
git commit -m "feat: apply active knowledge packs during mapping"
```

## Task 6: Knowledge API Router

**Files:**
- Create: `backend/app/api/v1/knowledge.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/knowledge.py`
- Modify: `backend/tests/test_api_contract_matrix.py`
- Modify: `backend/tests/test_mapping_knowledge.py`

- [ ] **Step 1: Write failing API tests**

Append to `backend/tests/test_mapping_knowledge.py`:

```python
from fastapi.testclient import TestClient

from app.api import deps
from app.main import create_app


@pytest.fixture()
def knowledge_api_context(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    storage = StorageService(tmp_path / "storage")
    app = create_app(init_database=False)

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_storage_service] = lambda: storage
    with TestClient(app, raise_server_exceptions=False) as client:
        with factory() as db:
            task_id = _seed_reviewed_task(db, storage)
        yield client, task_id


def test_knowledge_api_capture_derive_approve_pack_and_metrics(knowledge_api_context):
    client, task_id = knowledge_api_context

    run_response = client.post(f"/api/v1/knowledge/real-runs/from-task/{task_id}")
    assert run_response.status_code == 200
    real_run_id = run_response.json()["real_run_id"]

    derive_response = client.post(f"/api/v1/knowledge/real-runs/{real_run_id}/derive")
    assert derive_response.status_code == 200
    alias_candidate = next(
        item for item in derive_response.json()["items"]
        if item["candidate_type"] == "alias_candidate"
    )

    decision_response = client.post(
        f"/api/v1/knowledge/candidates/{alias_candidate['candidate_id']}/decision",
        json={
            "decision": "approved",
            "reviewer": "tester",
            "final_payload": {"aliases": ["doc_title"]},
            "reason": "reviewed",
        },
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"

    pack_response = client.post(
        "/api/v1/knowledge/packs",
        json={
            "name": "Title aliases",
            "scope": {"schema_id": "schema_k", "template_id": "template_k"},
            "candidate_ids": [alias_candidate["candidate_id"]],
            "reviewer": "tester",
        },
    )
    assert pack_response.status_code == 200
    assert pack_response.json()["status"] == "draft"

    metrics_response = client.get("/api/v1/knowledge/metrics")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["approved_candidates"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py::test_knowledge_api_capture_derive_approve_pack_and_metrics -q
```

Expected: FAIL with 404 for `/api/v1/knowledge/real-runs/from-task/{task_id}`.

- [ ] **Step 3: Add list and metrics service methods**

Add to `KnowledgeService`:

```python
    def list_candidates(self, status: str | None = None) -> list[LearningCandidateView]:
        query = self.db.query(LearningCandidateRecord)
        if status:
            query = query.filter(LearningCandidateRecord.status == status)
        records = query.order_by(LearningCandidateRecord.created_at.desc()).all()
        return [self._candidate_view(record) for record in records]

    def list_packs(self) -> list[KnowledgePackView]:
        records = (
            self.db.query(KnowledgePackRecord)
            .order_by(KnowledgePackRecord.created_at.desc())
            .all()
        )
        return [self._pack_view(record) for record in records]

    def activate_pack(self, pack_id: str) -> KnowledgePackView:
        pack = self.db.get(KnowledgePackRecord, pack_id)
        if pack is None:
            raise LookupError("knowledge pack not found")
        pack.status = "active"
        pack.activated_at = utcnow()
        self.db.commit()
        self.db.refresh(pack)
        return self._pack_view(pack)

    def metrics(self) -> KnowledgeMetricsResponse:
        return KnowledgeMetricsResponse(
            real_runs=self.db.query(RealRunRecord).count(),
            pending_candidates=self.db.query(LearningCandidateRecord)
            .filter(LearningCandidateRecord.status == "pending")
            .count(),
            approved_candidates=self.db.query(LearningCandidateRecord)
            .filter(LearningCandidateRecord.status == "approved")
            .count(),
            rejected_candidates=self.db.query(LearningCandidateRecord)
            .filter(LearningCandidateRecord.status == "rejected")
            .count(),
            active_packs=self.db.query(KnowledgePackRecord)
            .filter(KnowledgePackRecord.status == "active")
            .count(),
        )
```

- [ ] **Step 4: Add API router**

Create `backend/app/api/v1/knowledge.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.knowledge import (
    CandidateDecisionRequest,
    CandidateListResponse,
    KnowledgeMetricsResponse,
    KnowledgePackCreateRequest,
    KnowledgePackListResponse,
    KnowledgePackView,
    LearningCandidateView,
    RealRunView,
)
from app.services.knowledge_service import KnowledgeService, KnowledgeValidationError
from app.services.storage_service import StorageService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> KnowledgeService:
    return KnowledgeService(db, storage)


@router.post("/real-runs/from-task/{task_id}", response_model=RealRunView)
def capture_real_run(
    task_id: str,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> RealRunView:
    try:
        return service.capture_real_run(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/real-runs/{real_run_id}/derive", response_model=CandidateListResponse)
def derive_candidates(
    real_run_id: str,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> CandidateListResponse:
    try:
        return CandidateListResponse(items=service.derive_learning_candidates(real_run_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/candidates", response_model=CandidateListResponse)
def list_candidates(
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    status: Annotated[str | None, Query()] = None,
) -> CandidateListResponse:
    return CandidateListResponse(items=service.list_candidates(status=status))


@router.post("/candidates/{candidate_id}/decision", response_model=LearningCandidateView)
def decide_candidate(
    candidate_id: str,
    request: CandidateDecisionRequest,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> LearningCandidateView:
    try:
        return service.decide_candidate(candidate_id, request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/packs", response_model=KnowledgePackView)
def create_pack(
    request: KnowledgePackCreateRequest,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgePackView:
    try:
        return service.create_knowledge_pack(request)
    except KnowledgeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/packs/{pack_id}/activate", response_model=KnowledgePackView)
def activate_pack(
    pack_id: str,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgePackView:
    try:
        return service.activate_pack(pack_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/packs", response_model=KnowledgePackListResponse)
def list_packs(
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgePackListResponse:
    return KnowledgePackListResponse(items=service.list_packs())


@router.get("/metrics", response_model=KnowledgeMetricsResponse)
def get_metrics(
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgeMetricsResponse:
    return service.metrics()
```

Modify `backend/app/api/v1/router.py`:

```python
from app.api.v1.knowledge import router as knowledge_router
```

and include:

```python
api_router.include_router(knowledge_router)
```

- [ ] **Step 5: Update endpoint inventory**

Modify `backend/tests/test_api_contract_matrix.py`:

```python
    ("post", "/api/v1/knowledge/real-runs/from-task/{task_id}"),
    ("post", "/api/v1/knowledge/real-runs/{real_run_id}/derive"),
    ("get", "/api/v1/knowledge/candidates"),
    ("post", "/api/v1/knowledge/candidates/{candidate_id}/decision"),
    ("post", "/api/v1/knowledge/packs"),
    ("post", "/api/v1/knowledge/packs/{pack_id}/activate"),
    ("get", "/api/v1/knowledge/packs"),
    ("get", "/api/v1/knowledge/metrics"),
```

Change:

```python
    assert len(actual) == 28
```

to:

```python
    assert len(actual) == 36
```

- [ ] **Step 6: Run API tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py tests/test_api_contract_matrix.py::test_openapi_exposes_exact_mvp_endpoint_inventory -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/api/v1/knowledge.py backend/app/api/v1/router.py backend/app/services/knowledge_service.py backend/app/schemas/knowledge.py backend/tests/test_mapping_knowledge.py backend/tests/test_api_contract_matrix.py
git commit -m "feat: expose mapping knowledge review APIs"
```

## Task 7: Sanitized Fixture Export And Activation Gate

**Files:**
- Modify: `backend/app/services/knowledge_service.py`
- Modify: `backend/tests/test_mapping_knowledge.py`

- [ ] **Step 1: Write failing fixture export and activation tests**

Append to `backend/tests/test_mapping_knowledge.py`:

```python
def test_fixture_export_requires_approved_badcase_candidate(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)
    service = KnowledgeService(db, storage)
    run = service.capture_real_run(task_id)
    badcase = next(
        item for item in service.derive_learning_candidates(run.real_run_id)
        if item.candidate_type == "badcase_candidate"
    )

    with pytest.raises(ValueError, match="candidate must be approved"):
        service.export_fixture_candidate(badcase.candidate_id, "badcase")


def test_approved_badcase_exports_sanitized_fixture(knowledge_context):
    db, storage = knowledge_context
    task_id = _seed_reviewed_task(db, storage)
    service = KnowledgeService(db, storage)
    run = service.capture_real_run(task_id)
    badcase = next(
        item for item in service.derive_learning_candidates(run.real_run_id)
        if item.candidate_type == "badcase_candidate"
    )
    service.decide_candidate(
        badcase.candidate_id,
        CandidateDecisionRequest(
            decision="approved",
            reviewer="tester",
            final_payload={"case_type": "unmapped_required"},
            reason="safe fixture",
        ),
    )

    path = service.export_fixture_candidate(badcase.candidate_id, "badcase")
    data = storage.read_json(path)

    assert path.startswith("fixtures/badcases/")
    assert data["source"] == "sanitized_learning_candidate"
    assert "raw_uir" not in data
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py::test_fixture_export_requires_approved_badcase_candidate tests/test_mapping_knowledge.py::test_approved_badcase_exports_sanitized_fixture -q
```

Expected: FAIL with missing `export_fixture_candidate`.

- [ ] **Step 3: Implement sanitized fixture export**

Add to `KnowledgeService`:

```python
    def export_fixture_candidate(self, candidate_id: str, fixture_type: str) -> str:
        record = self._candidate(candidate_id)
        if record.status != "approved":
            raise KnowledgeValidationError("candidate must be approved before fixture export")
        if fixture_type not in {"eval", "badcase"}:
            raise KnowledgeValidationError("fixture_type must be eval or badcase")
        payload = {
            "source": "sanitized_learning_candidate",
            "candidate_id": record.candidate_id,
            "real_run_id": record.real_run_id,
            "task_id": record.task_id,
            "candidate_type": record.candidate_type,
            "target_field_id": record.target_field_id,
            "final_payload": json.loads(record.final_payload_json or "{}"),
            "evidence": json.loads(record.evidence_json or "{}"),
        }
        folder = "eval" if fixture_type == "eval" else "badcases"
        path = f"fixtures/{folder}/{record.candidate_id}.json"
        self.storage.save_json(path, payload)
        return path
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py -q
```

Expected: PASS for all knowledge tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/knowledge_service.py backend/tests/test_mapping_knowledge.py
git commit -m "feat: export sanitized knowledge fixtures"
```

## Task 8: Frontend API Types And Client

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/__tests__/knowledgePage.test.tsx`

- [ ] **Step 1: Write failing frontend API test**

Create `frontend/src/__tests__/knowledgePage.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";

import { api } from "../api/client";

describe("knowledge API client", () => {
  it("posts candidate decisions and creates knowledge packs", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            candidate_id: "lc_1",
            real_run_id: "run_1",
            task_id: "task_1",
            candidate_type: "alias_candidate",
            status: "approved",
            risk_level: "medium",
            target_field_id: "title",
            proposed_payload: { aliases: ["doc_title"] },
            final_payload: { aliases: ["doc_title"] },
            evidence: {},
            generator: "review_feedback",
            confidence: 0.95,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            pack_id: "kp_1",
            name: "Title aliases",
            scope: { schema_id: "schema_1" },
            status: "draft",
            version: "1.0.0",
            item_count: 1,
            regression_report_path: null,
            reviewer: "tester",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    const candidate = await api.decideKnowledgeCandidate("lc_1", {
      decision: "approved",
      reviewer: "tester",
      final_payload: { aliases: ["doc_title"] },
      reason: "reviewed",
    });
    const pack = await api.createKnowledgePack({
      name: "Title aliases",
      scope: { schema_id: "schema_1" },
      candidate_ids: ["lc_1"],
      reviewer: "tester",
    });

    expect(candidate.status).toBe("approved");
    expect(pack.pack_id).toBe("kp_1");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).decision).toBe("approved");
    fetchMock.mockRestore();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- knowledgePage
```

Expected: FAIL because `decideKnowledgeCandidate` and `createKnowledgePack` are not defined.

- [ ] **Step 3: Add frontend types**

Append to `frontend/src/api/types.ts`:

```ts
export interface LearningCandidateItem {
  candidate_id: string;
  real_run_id: string;
  task_id: string;
  candidate_type: string;
  status: "pending" | "approved" | "rejected" | "superseded";
  risk_level: "low" | "medium" | "high";
  target_field_id: string | null;
  proposed_payload: JsonObject;
  final_payload: JsonObject;
  evidence: JsonObject;
  generator: string;
  confidence: number;
}

export interface LearningCandidateListResponse {
  items: LearningCandidateItem[];
}

export interface CandidateDecisionPayload {
  decision: "approved" | "rejected";
  reviewer: string;
  final_payload?: JsonObject;
  reason: string;
}

export interface KnowledgePackItem {
  pack_id: string;
  name: string;
  scope: JsonObject;
  status: "draft" | "active" | "superseded";
  version: string;
  item_count: number;
  regression_report_path: string | null;
  reviewer: string;
}

export interface KnowledgePackCreatePayload {
  name: string;
  scope: JsonObject;
  candidate_ids: string[];
  reviewer: string;
}

export interface KnowledgePackListResponse {
  items: KnowledgePackItem[];
}

export interface KnowledgeMetricsResponse {
  real_runs: number;
  pending_candidates: number;
  approved_candidates: number;
  rejected_candidates: number;
  active_packs: number;
}
```

Keep the existing field-candidate `CandidateListResponse` unchanged. Use `LearningCandidateListResponse` only for mapping knowledge candidates.

- [ ] **Step 4: Add frontend client methods**

Modify the import list in `frontend/src/api/client.ts` to include:

```ts
  CandidateDecisionPayload,
  KnowledgeMetricsResponse,
  KnowledgePackCreatePayload,
  KnowledgePackItem,
  KnowledgePackListResponse,
  LearningCandidateListResponse,
```

Add methods inside `api`:

```ts
  captureKnowledgeRun(taskId: string) {
    return apiRequest<{ real_run_id: string }>(
      `/knowledge/real-runs/from-task/${taskId}`,
      { method: "POST", body: jsonBody({}) },
      "捕获真实运行",
    );
  },
  deriveKnowledgeCandidates(realRunId: string) {
    return apiRequest<LearningCandidateListResponse>(
      `/knowledge/real-runs/${realRunId}/derive`,
      { method: "POST", body: jsonBody({}) },
      "生成学习候选",
    );
  },
  listKnowledgeCandidates(status = "pending") {
    return apiRequest<LearningCandidateListResponse>(
      `/knowledge/candidates?status=${encodeURIComponent(status)}`,
      {},
      "加载学习候选",
    );
  },
  decideKnowledgeCandidate(candidateId: string, payload: CandidateDecisionPayload) {
    return apiRequest<LearningCandidateItem>(
      `/knowledge/candidates/${candidateId}/decision`,
      { method: "POST", body: jsonBody(payload) },
      "审核学习候选",
    );
  },
  createKnowledgePack(payload: KnowledgePackCreatePayload) {
    return apiRequest<KnowledgePackItem>(
      "/knowledge/packs",
      { method: "POST", body: jsonBody(payload) },
      "创建知识包",
    );
  },
  listKnowledgePacks() {
    return apiRequest<KnowledgePackListResponse>("/knowledge/packs", {}, "加载知识包");
  },
  activateKnowledgePack(packId: string) {
    return apiRequest<KnowledgePackItem>(
      `/knowledge/packs/${packId}/activate`,
      { method: "POST", body: jsonBody({}) },
      "启用知识包",
    );
  },
  getKnowledgeMetrics() {
    return apiRequest<KnowledgeMetricsResponse>("/knowledge/metrics", {}, "加载成长指标");
  },
```

- [ ] **Step 5: Run API client test**

Run:

```powershell
cd frontend
npm run test -- knowledgePage
```

Expected: PASS for the API client test.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/__tests__/knowledgePage.test.tsx
git commit -m "feat: add frontend knowledge API client"
```

## Task 9: Knowledge Review Page

**Files:**
- Create: `frontend/src/pages/KnowledgePage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/appTypes.ts`
- Modify: `frontend/src/navItems.ts`
- Modify: `frontend/src/__tests__/knowledgePage.test.tsx`

- [ ] **Step 1: Write failing page test**

Append to `frontend/src/__tests__/knowledgePage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { KnowledgePage } from "../pages/KnowledgePage";

describe("KnowledgePage", () => {
  it("loads pending candidates and approves one", async () => {
    vi.spyOn(api, "getKnowledgeMetrics").mockResolvedValue({
      real_runs: 1,
      pending_candidates: 1,
      approved_candidates: 0,
      rejected_candidates: 0,
      active_packs: 0,
    });
    vi.spyOn(api, "listKnowledgeCandidates").mockResolvedValue({
      items: [
        {
          candidate_id: "lc_1",
          real_run_id: "run_1",
          task_id: "task_1",
          candidate_type: "alias_candidate",
          status: "pending",
          risk_level: "medium",
          target_field_id: "title",
          proposed_payload: { aliases: ["doc_title"] },
          final_payload: {},
          evidence: { source_name: "doc_title" },
          generator: "review_feedback",
          confidence: 0.95,
        },
      ],
    });
    vi.spyOn(api, "listKnowledgePacks").mockResolvedValue({ items: [] });
    vi.spyOn(api, "decideKnowledgeCandidate").mockResolvedValue({
      candidate_id: "lc_1",
      real_run_id: "run_1",
      task_id: "task_1",
      candidate_type: "alias_candidate",
      status: "approved",
      risk_level: "medium",
      target_field_id: "title",
      proposed_payload: { aliases: ["doc_title"] },
      final_payload: { aliases: ["doc_title"] },
      evidence: { source_name: "doc_title" },
      generator: "review_feedback",
      confidence: 0.95,
    });

    render(<KnowledgePage onToast={vi.fn()} selection={{ docId: null, schemaId: null, templateId: null, taskId: null, taskStatus: null }} />);

    expect(await screen.findByText("alias_candidate")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /批准/i }));

    await waitFor(() => expect(api.decideKnowledgeCandidate).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- knowledgePage
```

Expected: FAIL because `KnowledgePage` does not exist.

- [ ] **Step 3: Add KnowledgePage**

Create `frontend/src/pages/KnowledgePage.tsx`:

```tsx
import { Brain, CheckCircle2, RotateCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  KnowledgeMetricsResponse,
  KnowledgePackItem,
  LearningCandidateItem,
} from "../api/types";
import type { ToastInput, WorkbenchSelection } from "../appTypes";

interface KnowledgePageProps {
  selection: WorkbenchSelection;
  onToast?: (toast: ToastInput) => void;
}

function jsonText(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function KnowledgePage({ selection, onToast }: KnowledgePageProps) {
  const [metrics, setMetrics] = useState<KnowledgeMetricsResponse | null>(null);
  const [candidates, setCandidates] = useState<LearningCandidateItem[]>([]);
  const [packs, setPacks] = useState<KnowledgePackItem[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [nextMetrics, nextCandidates, nextPacks] = await Promise.all([
      api.getKnowledgeMetrics(),
      api.listKnowledgeCandidates("pending"),
      api.listKnowledgePacks(),
    ]);
    setMetrics(nextMetrics);
    setCandidates(nextCandidates.items);
    setPacks(nextPacks.items);
  }, []);

  useEffect(() => {
    void refresh().catch((error) => {
      onToast?.({
        tone: "warning",
        title: "成长数据不可用",
        detail: error instanceof Error ? error.message : "无法加载成长指标。",
      });
    });
  }, [onToast, refresh]);

  async function captureCurrentTask() {
    if (!selection.taskId) {
      onToast?.({ tone: "warning", title: "请选择 Task", detail: "需要先选择一个真实运行 Task。" });
      return;
    }
    setBusy(true);
    try {
      const run = await api.captureKnowledgeRun(selection.taskId);
      await api.deriveKnowledgeCandidates(run.real_run_id);
      await refresh();
      onToast?.({ tone: "success", title: "学习候选已生成", detail: run.real_run_id });
    } finally {
      setBusy(false);
    }
  }

  async function decide(candidate: LearningCandidateItem, decision: "approved" | "rejected") {
    setBusy(true);
    try {
      await api.decideKnowledgeCandidate(candidate.candidate_id, {
        decision,
        reviewer: "human",
        final_payload: decision === "approved" ? candidate.proposed_payload : {},
        reason: decision === "approved" ? "人工批准" : "人工拒绝",
      });
      await refresh();
      onToast?.({ tone: "success", title: "学习候选已处理", detail: candidate.candidate_id });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="document-panel knowledge-page" aria-labelledby="knowledge-page-title">
      <div className="document-panel__header">
        <div>
          <span className="section-label">Mapping Knowledge</span>
          <h2 id="knowledge-page-title">映射成长中心</h2>
          <p>把人工确认后的映射证据沉淀为可审计的规则候选与知识包。</p>
        </div>
        <div className="button-row">
          <button className="secondary-button" disabled={busy} onClick={() => void refresh()} type="button">
            <RotateCw aria-hidden="true" size={15} />
            刷新
          </button>
          <button className="primary-button" disabled={busy || !selection.taskId} onClick={() => void captureCurrentTask()} type="button">
            <Brain aria-hidden="true" size={15} />
            从当前 Task 生成候选
          </button>
        </div>
      </div>

      <div className="metric-row">
        <div className="metric"><strong>{metrics?.real_runs ?? 0}</strong><span>真实运行</span></div>
        <div className="metric"><strong>{metrics?.pending_candidates ?? 0}</strong><span>待审核</span></div>
        <div className="metric"><strong>{metrics?.approved_candidates ?? 0}</strong><span>已批准</span></div>
        <div className="metric"><strong>{metrics?.active_packs ?? 0}</strong><span>启用知识包</span></div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>目标字段</th>
              <th>风险</th>
              <th>建议</th>
              <th>证据</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate) => (
              <tr key={candidate.candidate_id}>
                <td>{candidate.candidate_type}</td>
                <td>{candidate.target_field_id ?? "-"}</td>
                <td>{candidate.risk_level}</td>
                <td><pre>{jsonText(candidate.proposed_payload)}</pre></td>
                <td><pre>{jsonText(candidate.evidence)}</pre></td>
                <td>
                  <div className="button-row">
                    <button className="secondary-button" disabled={busy} onClick={() => void decide(candidate, "approved")} type="button">
                      <CheckCircle2 aria-hidden="true" size={15} />
                      批准
                    </button>
                    <button className="secondary-button" disabled={busy} onClick={() => void decide(candidate, "rejected")} type="button">
                      <XCircle aria-hidden="true" size={15} />
                      拒绝
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr><th>知识包</th><th>范围</th><th>状态</th><th>规则数</th></tr>
          </thead>
          <tbody>
            {packs.map((pack) => (
              <tr key={pack.pack_id}>
                <td>{pack.name}</td>
                <td><pre>{jsonText(pack.scope)}</pre></td>
                <td>{pack.status}</td>
                <td>{pack.item_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Wire navigation**

Modify `frontend/src/appTypes.ts`:

```ts
export type ViewId = "import" | "tasks" | "mapping" | "knowledge" | "detail" | "package";
```

Modify `frontend/src/navItems.ts`:

```ts
import { Archive, Brain, FileInput, FileText, GitBranch, ListChecks } from "lucide-react";
```

Add after Mapping:

```ts
  {
    id: "knowledge",
    label: "成长",
    description: "沉淀映射知识",
    icon: Brain,
  },
```

Modify `frontend/src/App.tsx` imports:

```tsx
import { KnowledgePage } from "./pages/KnowledgePage";
```

Add `VIEW_COPY.knowledge`:

```tsx
  knowledge: {
    title: "映射成长中心",
    body: "从人工复核和失败案例中沉淀受控映射知识。",
  },
```

Add in `renderView()` before detail:

```tsx
    if (activeView === "knowledge") {
      return <KnowledgePage onToast={pushToast} selection={selection} />;
    }
```

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
cd frontend
npm run test -- knowledgePage shell
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/pages/KnowledgePage.tsx frontend/src/App.tsx frontend/src/appTypes.ts frontend/src/navItems.ts frontend/src/__tests__/knowledgePage.test.tsx
git commit -m "feat: add mapping knowledge review page"
```

## Task 10: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/openapi.json`
- Test: backend and frontend verification commands

- [ ] **Step 1: Update README boundaries and endpoint list**

Add to `README.md` under features:

```markdown
- Controlled Mapping Knowledge growth loop for reviewed aliases, rules, badcases, and evaluation assets
- Human approval gate for all learned mapping knowledge before activation
```

Add to the Project Boundaries section:

```markdown
The Mapping Knowledge growth loop only learns mapping knowledge and evaluation assets. It does not train models, parse raw documents, clean data, normalize entities, or bypass human review for uncertain mappings.
```

Add API entries:

```markdown
POST /api/v1/knowledge/real-runs/from-task/{task_id}
POST /api/v1/knowledge/real-runs/{real_run_id}/derive
GET  /api/v1/knowledge/candidates
POST /api/v1/knowledge/candidates/{candidate_id}/decision
POST /api/v1/knowledge/packs
POST /api/v1/knowledge/packs/{pack_id}/activate
GET  /api/v1/knowledge/packs
GET  /api/v1/knowledge/metrics
```

- [ ] **Step 2: Refresh OpenAPI JSON**

Run:

```powershell
cd backend
.\.venv\Scripts\python - <<'PY'
import json
from app.main import create_app

schema = create_app(init_database=False).openapi()
with open("../docs/openapi.json", "w", encoding="utf-8") as handle:
    json.dump(schema, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
```

Expected: `docs/openapi.json` includes `/api/v1/knowledge/metrics`.

- [ ] **Step 3: Run backend verification**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_mapping_knowledge.py tests/test_effective_template_service.py tests/test_api_contract_matrix.py tests/test_phase10_llm_fallback.py -q
.\.venv\Scripts\python -m ruff check .
```

Expected: pytest PASS and Ruff reports no errors.

- [ ] **Step 4: Run frontend verification**

Run:

```powershell
cd frontend
npm run test -- knowledgePage workflowPages shell
npm run lint
npm run build
```

Expected: Vitest PASS, lint PASS, build PASS.

- [ ] **Step 5: Run full project smoke verification**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
cd ..\frontend
npm run test
```

Expected: backend and frontend suites pass.

- [ ] **Step 6: Commit**

```powershell
git add README.md docs/openapi.json
git commit -m "docs: document mapping knowledge growth workflow"
```

## Self-Review

Spec coverage:

- Real run collection is covered by Task 2 and API exposure in Task 6.
- Learning candidate extraction is covered by Task 2.
- Human approval and rejection are covered by Task 3 and frontend review in Task 9.
- Knowledge pack publishing and activation are covered by Tasks 3, 4, 5, and 6.
- Effective template replay evidence is covered by Task 5 through mapping report `knowledge_pack_ids`.
- Sanitized fixture export is covered by Task 7.
- Frontend review queue and metrics are covered by Tasks 8 and 9.
- Documentation and OpenAPI evidence are covered by Task 10.

Placeholder scan:

- The plan contains no incomplete sections, no undefined function names, and no unspecified test commands.

Type consistency:

- Backend schemas use `LearningCandidateView`, `KnowledgePackView`, and `KnowledgeMetricsResponse`.
- Frontend should use `LearningCandidateListResponse` for learning candidates to avoid conflict with the existing field-candidate list type.
