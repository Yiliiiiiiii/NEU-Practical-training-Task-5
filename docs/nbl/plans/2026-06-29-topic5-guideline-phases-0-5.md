# Topic 5 Guideline Phases 0–5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and verify every Phase 0–5 deliverable in `docs/guildline/2026.-6-29.md` without changing the UIR production boundary.

**Architecture:** Keep the existing production pipeline and services authoritative. Add deterministic, importable evaluation scripts around those services; expose only additive read APIs for evidence; render the results through focused frontend panels. Every phase writes honest JSON and Markdown reports and is committed only after its focused and regression checks pass.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy, pytest, Ruff, React 18, TypeScript, Vite 6, Vitest.

---

## File Structure

New evaluation scripts remain under `scripts/`; their tests live under
`backend/tests/` and load the scripts as importable modules. Versioned catalog
fixtures remain under `examples/production_like/`. Real-world decision/query
fixtures remain under `examples/real_world/`. Frontend evidence rendering is
split into one component per panel plus pure data helpers.

Generated reports are deterministic repository artifacts. `.gitignore` will
allowlist only the eight Phase 0/2/3/5 report files listed by the guideline;
package directories and temporary databases stay ignored.

### Task 1: Repair Clean-Checkout Reproducibility

**状态**
- [ ] 任务完成

**Dependencies:** None
**Parallelizable:** No (establishes the trustworthy baseline for every later task)

**Files:**
- Modify: `backend/tests/test_governance_security.py`
- Modify: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Modify: `README.md`
- Modify: `docs/developer_guide.md`

- [ ] **Step 1: Make the hidden SQLite dependency fail deterministically**

Add `monkeypatch.chdir(tmp_path)` and require an exact successful response:

```python
def test_api_key_auth_disabled_allows_existing_requests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = make_auth_client(tmp_path, enabled=False)

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
cd backend
F:\p2\backend\.venv\Scripts\python.exe -m pytest -q tests/test_governance_security.py::test_api_key_auth_disabled_allows_existing_requests
```

Expected: fail with `sqlite3.OperationalError: no such table: conversion_tasks`.

- [ ] **Step 3: Isolate the authentication test database**

Refactor the helper to construct and initialize a temporary database and
override the same dependency used by the route:

```python
def make_auth_client(tmp_path, *, enabled: bool) -> TestClient:
    from app.api.deps import get_db

    engine = create_engine(
        f"sqlite:///{tmp_path / 'auth.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    app = create_app(
        Settings(
            storage_root=str(tmp_path / "storage"),
            database_url=f"sqlite:///{tmp_path / 'auth.db'}",
            api_key_auth_enabled=enabled,
            api_keys="dev-key",
            _env_file=None,
        )
    )

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)
```

- [ ] **Step 4: Verify the database test is GREEN**

Run the focused test and then the full backend suite. Expected: focused pass
and `129 passed` or more in the full suite.

- [ ] **Step 5: Pin valid frontend dependencies**

Replace invalid `^latest` declarations and add the test command:

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "test": "vitest",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 127.0.0.1"
  },
  "dependencies": {
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/react": "^18.3.31",
    "@types/react-dom": "^18.3.7",
    "@vitejs/plugin-react": "^4.7.0",
    "jsdom": "^25.0.1",
    "typescript": "^5.9.3",
    "vite": "^6.4.3",
    "vitest": "^2.1.9"
  }
}
```

Generate the lock file with `npm install`, remove the temporary junction before
installing if present, then run `npm test -- --run --passWithNoTests` and
`npm run build`. Expected: clean install and build exit 0.

- [ ] **Step 6: Update setup documentation**

Document `npm ci` for reproducible installs and state that tests create their
own temporary databases.

- [ ] **Step 7: Commit**

```powershell
git add backend/tests/test_governance_security.py frontend/package.json frontend/package-lock.json README.md docs/developer_guide.md
git commit -m "fix: make clean checkout verification reproducible"
```

### Task 2: Phase 0 Acceptance Report

**状态**
- [ ] 任务完成

**Dependencies:** Task 1
**Parallelizable:** No (the acceptance aggregator becomes the final evidence sink)

**Files:**
- Create: `scripts/build_acceptance_report.py`
- Create: `backend/tests/test_acceptance_report_script.py`
- Modify: `.gitignore`
- Generate: `reports/acceptance_report.json`
- Generate: `reports/acceptance_report.md`
- Generate: `docs/acceptance_report.md`

- [ ] **Step 1: Write failing report tests**

Cover missing inputs, a minimal mock input, required JSON keys, and required
Markdown text:

```python
def test_missing_reports_are_recorded_instead_of_crashing(tmp_path):
    module = load_script()
    report = module.build_acceptance_report(tmp_path)
    assert report["checks"]["production_like_eval"]["status"] == "missing"
    assert report["checks"]["production_like_eval"]["reason"] == "report file not found"


def test_write_reports_emits_json_markdown_and_docs_copy(tmp_path):
    module = load_script()
    source = tmp_path / "reports" / "production_like_eval_report.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"summary":{"total_cases":15}}', encoding="utf-8")

    paths = module.write_reports(tmp_path, module.build_acceptance_report(tmp_path))

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "checks" in payload and "boundaries" in payload
    assert "课题 5" in markdown
    assert "UIR -> Schema -> Mapping" in markdown
    assert paths["docs"].is_file()
```

- [ ] **Step 2: Run tests and verify RED**

Expected: import/file-not-found failure for `scripts/build_acceptance_report.py`.

- [ ] **Step 3: Implement deterministic aggregation**

Create these public functions:

```python
REPORT_SPECS = {
    "production_like_eval": (
        "reports/production_like_eval_report.json",
        "python scripts/eval_production_like.py",
    ),
    "real_world_eval": (
        "reports/real_world_eval_report.json",
        "python scripts/eval_real_world_uir.py --base-url http://127.0.0.1:8000",
    ),
}


def read_json_report(root: Path, relative_path: str, command: str) -> dict[str, Any]:
    path = root / relative_path
    if not path.is_file():
        return {
            "status": "missing",
            "reason": "report file not found",
            "report_path": relative_path,
            "recommended_command": command,
            "summary": {},
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"status": "present", "report_path": relative_path, "summary": payload.get("summary", {})}


def build_acceptance_report(root: Path) -> dict[str, Any]:
    return {
        "project": "SchemaPack Agent",
        "topic": "Topic 5 数据格式标准化转换智能体",
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline": ["UIR", "Schema", "Mapping", "Transform", "Canonical", "Render", "Validate", "Manifest", "ZIP"],
        "checks": {
            name: read_json_report(root, path, command)
            for name, (path, command) in REPORT_SPECS.items()
        },
        "boundaries": [
            "production starts from UIR",
            "no OCR production parsing",
            "no full RAG",
            "no model training",
            "LLM suggestions are review-required",
        ],
    }
```

Implement `render_markdown(report)` with the fourteen required headings and
`write_reports(root, report)` with UTF-8, stable key ordering, and parent
directory creation.

- [ ] **Step 4: Verify focused tests and generate reports**

Run:

```powershell
cd backend
F:\p2\backend\.venv\Scripts\python.exe -m pytest -q tests/test_acceptance_report_script.py
cd ..
F:\p2\backend\.venv\Scripts\python.exe scripts/build_acceptance_report.py
```

Expected: tests pass and all three report/document paths exist.

- [ ] **Step 5: Allowlist generated Phase reports**

Keep `reports/*` ignored, then add explicit negated entries for acceptance,
knowledge-loop, retrieval, and LLM JSON/Markdown reports.

- [ ] **Step 6: Run Phase 0 regression checks and commit**

Run backend pytest and Ruff, then:

```powershell
git add .gitignore scripts/build_acceptance_report.py backend/tests/test_acceptance_report_script.py reports/acceptance_report.json reports/acceptance_report.md docs/acceptance_report.md
git commit -m "feat: generate topic 5 acceptance evidence report"
```

### Task 3: Phase 1 Procurement Schema, Template, and Evaluation Routing

**状态**
- [ ] 任务完成

**Dependencies:** Task 2
**Parallelizable:** No (later real-world and knowledge-loop metrics depend on this catalog)

**Files:**
- Create: `examples/production_like/schemas/procurement_doc_v1.json`
- Create: `examples/production_like/mapping_templates/procurement_doc_base_v1.json`
- Create: `examples/production_like/expected/procurement_mapping_gold_cases.jsonl`
- Create: `backend/tests/test_procurement_schema_template.py`
- Create: `backend/tests/test_procurement_mapping.py`
- Modify: `scripts/eval_real_world_uir.py`
- Modify: `docs/real_world_uir_dataset.md`

- [ ] **Step 1: Write failing fixture validity tests**

```python
def test_procurement_schema_and_template_load():
    schema = SchemaService().load_schema("procurement_doc")
    template = TemplateService().load_template("procurement_doc_base_v1")
    assert schema.version == "1.0.0"
    assert template.schema_id == schema.schema_id
    TemplateService().validate_template(template, schema)


def test_catalog_seed_discovers_procurement(db_session):
    service = CatalogGovernanceService(db_session)
    service.seed_from_files()
    assert service.load_schema("procurement_doc").schema_id == "procurement_doc"
    assert service.load_template("procurement_doc_base_v1").schema_id == "procurement_doc"
```

- [ ] **Step 2: Run validity tests and verify RED**

Expected: lookup failure for `procurement_doc`.

- [ ] **Step 3: Add the procurement schema**

Declare these exact field IDs:

```python
PROCUREMENT_FIELDS = [
    ("document_title", "string", True),
    ("notice_type", "string", True),
    ("project_name", "string", True),
    ("project_id", "string", False),
    ("buyer_name", "string", False),
    ("agency_name", "string", False),
    ("supplier_name", "string", False),
    ("budget_amount", "number", False),
    ("winning_amount", "number", False),
    ("currency", "string", False),
    ("procurement_method", "string", False),
    ("notice_date", "date", False),
    ("deadline", "datetime", False),
    ("contact_person", "string", False),
    ("contact_phone", "string", False),
    ("contact_address", "string", False),
    ("source_url", "string", True),
    ("source_site", "string", True),
]
```

Mirror required fields and types in `json_schema`, including enums for canonical
notice and procurement-method values.

- [ ] **Step 4: Add the procurement mapping template**

Provide explicit aliases for every field, regex rules for project ID, amounts,
notice date, and deadline, `currency: CNY`, and these enum maps:

```json
{
  "notice_type": {
    "采购公告": "procurement_notice",
    "招标公告": "tender_notice",
    "中标公告": "award_notice",
    "成交公告": "award_notice",
    "更正公告": "correction_notice",
    "结果公告": "result_notice"
  },
  "procurement_method": {
    "公开招标": "open_tender",
    "竞争性磋商": "competitive_consultation",
    "竞争性谈判": "competitive_negotiation",
    "询价": "inquiry",
    "单一来源": "single_source"
  }
}
```

- [ ] **Step 5: Write failing mapping behavior tests**

Use real `CandidateService` and `MappingService` to assert:

```python
assert mapped_target(report, "采购项目名称") == "project_name"
assert mapped_target(report, "预算金额") == "budget_amount"
assert mapped_target(report, "中标金额") == "winning_amount"
assert not crossed_amount_targets(report)
assert ambiguous_multiple_amounts(report).status == "review_required"
```

- [ ] **Step 6: Make procurement mapping tests GREEN**

Adjust fixture aliases/regex confidence only. Change production mapping logic
only if a failing test proves existing ambiguity handling is insufficient; in
that case add the smallest badcase/risk rule and retain strategy order.

- [ ] **Step 7: Route real-world procurement explicitly**

Introduce:

```python
DOCUMENT_CATALOG = {
    "policy_doc": ("policy_doc", "policy_doc_base_v1"),
    "meeting_doc": ("meeting_doc", "meeting_doc_base_v1"),
    "procurement_doc": ("procurement_doc", "procurement_doc_base_v1"),
    "general_doc": ("general_doc", "general_doc_base_v1"),
}
```

If either procurement catalog item is absent, record
`catalog_status: "missing"` and fail that sample visibly. Do not substitute
`general_doc`.

- [ ] **Step 8: Run Phase 1 verification and commit**

Run procurement tests, full pytest, Ruff, production-like evaluation, and the
catalog API tests. Commit:

```powershell
git add examples/production_like backend/tests/test_procurement_schema_template.py backend/tests/test_procurement_mapping.py scripts/eval_real_world_uir.py docs/real_world_uir_dataset.md
git commit -m "feat: add dedicated procurement schema and mapping"
```

### Task 4: Phase 2 Real-World Knowledge Loop

**状态**
- [ ] 任务完成

**Dependencies:** Task 3
**Parallelizable:** No (uses the dedicated procurement catalog and feeds the frontend comparison)

**Files:**
- Create: `examples/real_world/review_fixtures/procurement_review_decisions.jsonl`
- Create: `scripts/eval_real_world_knowledge_loop.py`
- Create: `backend/tests/test_real_world_knowledge_loop.py`
- Create: `docs/real_world_knowledge_loop.md`
- Generate: `reports/real_world_knowledge_loop_report.json`
- Generate: `reports/real_world_knowledge_loop_report.md`

- [ ] **Step 1: Add explicit approve/reject decisions**

Include at least one safe approval and one semantic rejection:

```json
{"source_field":"采购单位","target_field":"buyer_name","decision":"approve","reason":"采购单位与采购人语义一致"}
{"source_field":"最高限价","target_field":"winning_amount","decision":"reject","reason":"最高限价不是中标金额"}
```

- [ ] **Step 2: Write failing knowledge-loop tests**

Test pure decision loading plus existing service behavior:

```python
def test_only_approved_non_badcase_decisions_activate(tmp_path):
    result = run_loop(tmp_path, decisions=DECISIONS)
    assert result["approved_candidates"] == 1
    assert result["rejected_candidates"] == 1
    assert result["badcase_violation_count"] == 0
    assert "采购单位" in result["activated_aliases"]


def test_activation_does_not_mutate_old_snapshot(tmp_path):
    result = run_loop(tmp_path, decisions=DECISIONS)
    assert result["old_snapshot_unchanged"] is True
```

- [ ] **Step 3: Run tests and verify RED**

Expected: missing script/module.

- [ ] **Step 4: Implement an isolated evaluation context**

Create:

```python
@contextmanager
def evaluation_context(root: Path):
    work = TemporaryDirectory()
    engine = create_engine(
        f"sqlite:///{Path(work.name) / 'knowledge-loop.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as db:
        yield db, StorageService(Path(work.name) / "storage")
    work.cleanup()
```

Use `TaskExecutionService`, `ReviewKnowledgeWorkflowService`, and effective
template resolution. Persist a serialized baseline snapshot before activation,
rerun with a new task afterward, and compare the original bytes.

- [ ] **Step 5: Implement metrics and reports**

Expose:

```python
def collect_metrics(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "auto_mapped_fields": sum(item["auto_mapped_fields"] for item in results),
        "review_required_count": sum(item["review_required_count"] for item in results),
        "missing_required_count": sum(item["missing_required_count"] for item in results),
    }
```

The top-level report must contain all twelve guideline metrics, per-decision
evidence, remaining ambiguous cases, and a before/after Markdown table.

- [ ] **Step 6: Verify focused behavior and generate both reports**

Run the focused test, then:

```powershell
F:\p2\backend\.venv\Scripts\python.exe scripts/eval_real_world_knowledge_loop.py
```

Expected: both reports exist, `badcase_violation_count == 0`, and
`old_snapshot_unchanged == true`.

- [ ] **Step 7: Run Phase 2 regression and commit**

```powershell
git add examples/real_world/review_fixtures scripts/eval_real_world_knowledge_loop.py backend/tests/test_real_world_knowledge_loop.py docs/real_world_knowledge_loop.md reports/real_world_knowledge_loop_report.*
git commit -m "feat: evaluate real-world knowledge review loop"
```

### Task 5: Phase 3 Chunk Retrieval Evaluation

**状态**
- [ ] 任务完成

**Dependencies:** Task 4
**Parallelizable:** No (strict guideline phase order; frontend consumes its chunk evidence model)

**Files:**
- Create: `examples/real_world/retrieval_queries.jsonl`
- Create: `scripts/eval_chunk_retrieval.py`
- Create: `backend/tests/test_chunk_retrieval_eval.py`
- Generate: `reports/chunk_retrieval_eval_report.json`
- Generate: `reports/chunk_retrieval_eval_report.md`

- [ ] **Step 1: Add traceable query fixtures**

Each line has `query_id`, `doc_id`, `query`, `expected_terms`,
`expected_block_ids`, and `answer_field`. Cover procurement amount, policy
scope, meeting date/topic, and at least one table answer.

- [ ] **Step 2: Write failing metric tests**

```python
def test_recall_mrr_and_ndcg():
    ranked = [{"relevant": False}, {"relevant": True}, {"relevant": False}]
    assert recall_at_k(ranked, 1) == 0.0
    assert recall_at_k(ranked, 3) == 1.0
    assert reciprocal_rank(ranked) == 0.5
    assert ndcg_at_k(ranked, 5) == pytest.approx(1 / math.log2(3))


def test_empty_queries_and_chunks_write_reports(tmp_path):
    result = evaluate([], {}, strategies=["fixed_window"])
    paths = write_reports(tmp_path, result)
    assert result["status"] == "no_queries"
    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
```

- [ ] **Step 3: Run tests and verify RED**

Expected: missing script/module.

- [ ] **Step 4: Implement deterministic scoring**

```python
def score_chunk(query: dict[str, Any], chunk: dict[str, Any]) -> float:
    fields = [
        str(chunk.get("text", "")),
        str(chunk.get("summary", "")),
        " ".join(chunk.get("keywords", [])),
        " ".join(chunk.get("title_path", [])),
    ]
    searchable = "\n".join(fields).lower()
    terms = tokenize(str(query["query"]))
    score = sum(searchable.count(term) for term in terms)
    score += 3 * sum(term.lower() in searchable for term in query["expected_terms"])
    return float(score)


def is_relevant(query: dict[str, Any], chunk: dict[str, Any]) -> bool:
    return bool(set(query["expected_block_ids"]) & set(chunk.get("source_block_ids", [])))
```

Tokenization uses Latin words and Chinese 2–4 character n-grams. Stable ties
sort by `chunk_id`.

- [ ] **Step 5: Generate chunks through production services**

Build canonical inputs from each UIR and call `ChunkOrganizerService` once per
strategy with identical target/min/max/overlap values. Do not create a vector
database or call an LLM.

- [ ] **Step 6: Compute strategy metrics**

Implement Recall@1/3/5, MRR, nDCG@5, source-link coverage, table integrity,
average token estimate, and chunk count. Include per-query ranks and actual
failure analysis when the success criteria are not met.

- [ ] **Step 7: Verify, generate reports, and commit**

Run focused tests, full pytest/Ruff, and:

```powershell
F:\p2\backend\.venv\Scripts\python.exe scripts/eval_chunk_retrieval.py
```

Then commit the script, tests, fixture, and both reports.

### Task 6: Add Read-Only Manifest and Evaluation Report APIs

**状态**
- [ ] 任务完成

**Dependencies:** Task 5
**Parallelizable:** No (frontend types and panels depend on these payloads)

**Files:**
- Modify: `backend/app/services/package_service.py`
- Modify: `backend/app/services/task_execution_service.py`
- Create: `backend/app/api/v1/evaluation_reports.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/schemas/api.py`
- Modify: `backend/tests/test_task_execution_api.py`
- Create: `backend/tests/test_evaluation_reports_api.py`
- Modify: `docs/openapi.json`

- [ ] **Step 1: Write failing manifest report test**

```python
def test_task_manifest_report_lists_verified_files(client):
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id)
    assert client.post(f"/api/v1/tasks/{task_id}/execute").status_code == 200

    response = client.get(f"/api/v1/tasks/{task_id}/reports/manifest")

    assert response.status_code == 200
    assert response.json()["files"]
    assert all("sha256" in item for item in response.json()["files"])
```

- [ ] **Step 2: Run and verify RED**

Expected: 404 `report not found`.

- [ ] **Step 3: Carry the manifest through package creation**

Extend:

```python
@dataclass(frozen=True)
class PackageResult:
    metadata: OutputPackageMetadata
    verifier_report: ConsistencyReport
    manifest: Manifest
```

Return the built manifest, pass `manifest.model_dump(mode="json")` into
`_write_execution_artifacts`, write `tasks/{task_id}/manifest.json`, and add:

```python
REPORT_KEYS = {
    "mapping": "mapping_report",
    "validation": "validation_report",
    "transform": "transform_report",
    "canonical": "canonical",
    "content": "content_json",
    "chunks": "chunks",
    "verifier": "verifier_report",
    "content_organization": "content_organization_report",
    "content-organization": "content_organization_report",
    "manifest": "manifest",
}
```

- [ ] **Step 4: Verify manifest GREEN**

Run the focused task API test and package verifier tests.

- [ ] **Step 5: Write failing evaluation-report API tests**

```python
def test_knowledge_loop_report_returns_unavailable_when_missing(client, tmp_path):
    response = client.get("/api/v1/evaluation-reports/real-world-knowledge-loop")
    assert response.status_code == 200
    assert response.json()["status"] in {"available", "unavailable"}


def test_unknown_evaluation_report_is_rejected(client):
    response = client.get("/api/v1/evaluation-reports/not-allowed")
    assert response.status_code == 404
```

- [ ] **Step 6: Implement allowlisted read-only report route**

Use a fixed mapping:

```python
REPORTS = {
    "real-world-knowledge-loop": Path("reports/real_world_knowledge_loop_report.json")
}
```

Resolve against the repository root, never accept a caller-supplied filesystem
path, return `{"status": "unavailable", "recommended_command": ...}` when
missing, and otherwise return `{"status": "available", "report": payload}`.

- [ ] **Step 7: Export OpenAPI, verify, and commit**

Run focused tests, full backend checks, and
`scripts/export_openapi.py`; commit the additive API and snapshot.

### Task 7: Phase 4 Frontend Evidence Panels

**状态**
- [ ] 任务完成

**Dependencies:** Task 6
**Parallelizable:** No (integrates all preceding evidence payloads)

**Files:**
- Create: `frontend/src/evidence.ts`
- Create: `frontend/src/evidence.test.ts`
- Create: `frontend/src/components/MappingEvidencePanel.tsx`
- Create: `frontend/src/components/ValidationIssuePanel.tsx`
- Create: `frontend/src/components/ChunkEvidencePanel.tsx`
- Create: `frontend/src/components/PackageManifestPanel.tsx`
- Create: `frontend/src/components/KnowledgeComparisonPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing pure helper tests**

```typescript
import { describe, expect, it } from "vitest";
import { filterChunks, suggestedAction, truncateSha } from "./evidence";

describe("evidence helpers", () => {
  it("keeps table chunks with quality findings", () => {
    const chunks = [
      { chunk_id: "a", content_tags: ["table"], quality_flags: ["oversized"] },
      { chunk_id: "b", content_tags: ["paragraph"], quality_flags: [] }
    ];
    expect(filterChunks(chunks, { strategy: "all", tablesOnly: true, flaggedOnly: true }))
      .toEqual([chunks[0]]);
  });

  it("uses deterministic validation advice", () => {
    expect(suggestedAction({ severity: "error", message: "missing" }))
      .toBe("Review the source evidence and complete or reject this field.");
  });

  it("preserves the full checksum outside compact display", () => {
    expect(truncateSha("a".repeat(64))).toBe("aaaaaaaaaaaa…aaaaaaaa");
  });
});
```

- [ ] **Step 2: Run Vitest and verify RED**

Run `npm test -- --run src/evidence.test.ts`. Expected: missing module
or exported helper failure.

- [ ] **Step 3: Implement pure evidence helpers**

Implement typed, deterministic `filterChunks`, `suggestedAction`, mapping status
tone, manifest verification merge, and SHA truncation. Do not invent field
values.

- [ ] **Step 4: Implement the five focused components**

Each component accepts data and filter/action props only. It must render:

```typescript
export type MappingEvidencePanelProps = { report: MappingReport | null };
export type ValidationIssuePanelProps = { report: ValidationReport | null };
export type ChunkEvidencePanelProps = { report: ChunksReport | null };
export type PackageManifestPanelProps = {
  manifest: PackageManifest | null;
  verifier: VerifierReport | null;
};
export type KnowledgeComparisonPanelProps = {
  result: KnowledgeLoopApiResponse | null;
};
```

Use native buttons, selects, details/summary, tables, and existing icons. Show
all low-confidence/review/badcase rows; add strategy/table/quality filters;
render parent-child IDs; show full SHA inside expanded details; show the exact
knowledge-loop command when unavailable.

- [ ] **Step 5: Integrate API types and fetches**

Add `api.getManifestReport(taskId)`,
`api.getVerifierReport(taskId)`, and `api.getKnowledgeLoopReport()`. Extend
`refreshArtifacts` without changing the import/create/execute sequence.

- [ ] **Step 6: Replace inline report fragments in App**

Keep workflow controls and existing raw JSON details, but delegate the five
evidence sections to the new components. Add responsive styles without a UI
framework.

- [ ] **Step 7: Verify frontend and backend contract**

Run:

```powershell
cd frontend
npm test -- --run
npm run build
cd ..\backend
F:\p2\backend\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests and build pass.

- [ ] **Step 8: Commit**

Commit the helper, tests, components, App/API/types/styles, and no generated
`dist` files.

### Task 8: Phase 5 LLM Fallback Evaluation

**状态**
- [ ] 任务完成

**Dependencies:** Task 7
**Parallelizable:** No (strict guideline order and acceptance report aggregation)

**Files:**
- Create: `scripts/eval_llm_fallback_modes.py`
- Create: `backend/tests/test_llm_fallback_eval.py`
- Generate: `reports/llm_fallback_eval_report.json`
- Generate: `reports/llm_fallback_eval_report.md`

- [ ] **Step 1: Write failing disabled/stub evaluation tests**

```python
def test_disabled_mode_never_calls_provider(tmp_path):
    result = evaluate_mode("disabled", root=tmp_path)
    assert result["suggestion_count"] == 0
    assert result["auto_accepted_count"] == 0


def test_stub_suggestions_require_review_and_redact_secrets(tmp_path):
    result = evaluate_mode("stub", root=tmp_path, secret="sk-test-secret-value")
    assert result["suggestion_count"] > 0
    assert result["review_required_count"] == result["suggestion_count"]
    assert result["auto_accepted_count"] == 0
    assert result["secret_redaction_passed"] is True
    assert "sk-test-secret-value" not in json.dumps(result)
```

Add strict/non-strict provider-error and badcase-block tests.

- [ ] **Step 2: Run tests and verify RED**

Expected: missing script/module.

- [ ] **Step 3: Implement mode configuration**

```python
def settings_for_mode(mode: str) -> Settings:
    if mode == "disabled":
        return Settings(llm_mode="disabled", llm_fallback_enabled=False, _env_file=None)
    if mode == "stub":
        return Settings(llm_mode="mock", llm_fallback_enabled=True, _env_file=None)
    if mode == "openai-compatible":
        return Settings(llm_mode="openai_compatible", llm_fallback_enabled=True)
    raise ValueError(f"unsupported mode: {mode}")
```

Reject `openai-compatible` unless `--allow-network` is present. Never require a
real key for disabled/stub tests.

- [ ] **Step 4: Measure safety and failure behavior**

Run deterministic cases through `LLMFallbackService` and `MappingService`.
Count suggestions, review-required, auto-accepted, badcase-blocked, provider
errors, timeouts, and latency. Serialize only safe configuration snapshots and
hash metadata.

- [ ] **Step 5: Generate JSON and Markdown**

The report includes all guideline metrics. Assert before writing:

```python
if metrics["auto_accepted_count"] != 0:
    raise AssertionError("LLM suggestions must never be auto-accepted")
if not metrics["secret_redaction_passed"]:
    raise AssertionError("secret redaction failed")
```

- [ ] **Step 6: Verify and commit**

Run focused tests, disabled CLI, stub CLI, full pytest/Ruff, then commit the
script, tests, and two reports. Do not run network mode unless credentials are
explicitly supplied for that invocation.

### Task 9: Final Documentation, Acceptance Regeneration, and Full Verification

**状态**
- [ ] 任务完成

**Dependencies:** Task 8
**Parallelizable:** No (final evidence must reflect every prior phase)

**Files:**
- Modify: `README.md`
- Modify: `docs/developer_guide.md`
- Modify: `docs/real_world_uir_dataset.md`
- Modify: `docs/final_handoff_status.md`
- Modify: `docs/requirement_mapping.md`
- Modify: `docs/acceptance_report.md`
- Modify: `reports/acceptance_report.json`
- Modify: `reports/acceptance_report.md`

- [ ] **Step 1: Add a delivery checklist test**

Extend `test_acceptance_report_script.py` to assert every required guideline
artifact exists and every generated report has matching JSON/Markdown files.
Run it before documentation changes; expected failure if any artifact is still
missing.

- [ ] **Step 2: Close any artifact gap**

Create no new capabilities here. If the checklist fails, return to the owning
task, add its missing test/implementation/report, and rerun that phase.

- [ ] **Step 3: Update handoff documentation**

Document exact commands, real metric summaries, retained ambiguous cases,
boundaries, report paths, frontend panels, and the fact that network LLM
evaluation is optional and skipped unless explicitly run.

- [ ] **Step 4: Regenerate all deterministic reports**

Run:

```powershell
F:\p2\backend\.venv\Scripts\python.exe scripts/eval_production_like.py
F:\p2\backend\.venv\Scripts\python.exe scripts/eval_real_world_knowledge_loop.py
F:\p2\backend\.venv\Scripts\python.exe scripts/eval_chunk_retrieval.py
F:\p2\backend\.venv\Scripts\python.exe scripts/eval_llm_fallback_modes.py --mode stub
F:\p2\backend\.venv\Scripts\python.exe scripts/build_acceptance_report.py
```

- [ ] **Step 5: Run the complete verification gate**

```powershell
cd backend
F:\p2\backend\.venv\Scripts\python.exe -m pytest -q
F:\p2\backend\.venv\Scripts\python.exe -m ruff check .
cd ..\frontend
npm test -- --run
npm run build
cd ..
F:\p2\backend\.venv\Scripts\python.exe scripts/verify_all.py --check-openapi
```

Start a temporary backend and run `eval_real_world_uir.py` against it. Confirm
procurement uses `procurement_doc`, every generated package verifies, and the
process is stopped cleanly.

- [ ] **Step 6: Audit acceptance criteria**

Read the guideline checklist line by line and record the actual state in
`docs/acceptance_report.md`. Required assertions:

```text
badcase_violation_count = 0
auto_accepted_count = 0
secret_redaction_passed = true
old_snapshot_unchanged = true
production boundary = UIR
```

- [ ] **Step 7: Commit final evidence**

```powershell
git add README.md docs reports
git commit -m "docs: finalize topic 5 acceptance evidence"
```

---

## Plan Self-Review

- Spec coverage: prerequisite repairs and Phases 0–5 each have an owning task.
- Dependency consistency: procurement precedes the real-world knowledge loop;
  reports precede frontend consumption; all phase reports precede final
  acceptance regeneration.
- API compatibility: only new report names and a read-only endpoint are added.
- Boundary check: no production raw-source parsing, RAG, vector database,
  training, or autonomous LLM acceptance is introduced.
- Verification: every phase has focused tests and regression gates; final
  claims require fresh full-suite evidence.

---
**Execution Mode:** serial
