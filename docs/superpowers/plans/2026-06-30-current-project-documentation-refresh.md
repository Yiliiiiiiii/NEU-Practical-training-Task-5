# Current Project Documentation Refresh Implementation Plan

> **Historical plan:** Preserved as an execution record. Current status: [`../../project_status.md`](../../project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every canonical project document describe the verified behavior, evidence, commands, and limitations of the integrated `main` branch.

**Architecture:** Treat executable repository artifacts and committed JSON reports as the source of truth. Keep the README concise, make the final handoff the authoritative status record, and assign setup, API, deployment, demo, package, requirement, and dataset details to focused documents. Historical plans, source guidance, and timestamped evidence remain unchanged.

**Tech Stack:** Markdown, PowerShell, Git, FastAPI OpenAPI JSON, Pytest, Ruff, React/Vite, and the repository evaluation scripts.

---

### Task 1: Capture And Lock The Current Fact Baseline

**Files:**
- Read: `scripts/verify_all.py`
- Read: `docs/openapi.json`
- Read: `frontend/package.json`
- Read: `examples/production_like/schemas/*.json`
- Read: `examples/production_like/mapping_templates/*.json`
- Read: `examples/real_world/uir/**/*.json`
- Read: `reports/real_world_eval_report.json`
- Read: `reports/real_world_mapping_eval_report.json`
- Read: `reports/procurement_doc_eval_report.json`
- Read: `reports/content_organization_retrieval_eval.json`
- Read: `reports/knowledge_loop_eval_report.json`
- Read: `reports/real_world_knowledge_loop_report.json`
- Read: `reports/llm_fallback_eval_report.json`

- [ ] **Step 1: Confirm the integrated branch and clean working tree**

Run:

```powershell
git branch --show-current
git status --short --branch
```

Expected:

```text
main
## main
```

- [ ] **Step 2: Run the unified verification gate**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected:

```text
202 passed
All checks passed!
✓ built
exported 32 paths
```

- [ ] **Step 3: Assert repository inventory counts**

Run:

```powershell
$api = Get-Content -Raw -Encoding UTF8 docs\openapi.json | ConvertFrom-Json
$paths = @($api.paths.PSObject.Properties.Name)
$schemas = @(Get-ChildItem examples\production_like\schemas -Filter *.json)
$templates = @(Get-ChildItem examples\production_like\mapping_templates -Filter *.json)
$uir = @(
  Get-ChildItem examples\real_world\uir -Recurse -Filter *.json |
    Where-Object { $_.FullName -notmatch '\\_rejected\\' }
)
if ($paths.Count -ne 32) { throw "Expected 32 OpenAPI paths, got $($paths.Count)" }
if ($schemas.Count -ne 5) { throw "Expected 5 schemas, got $($schemas.Count)" }
if ($templates.Count -ne 5) { throw "Expected 5 templates, got $($templates.Count)" }
if ($uir.Count -ne 16) { throw "Expected 16 real-world UIR files, got $($uir.Count)" }
```

Expected: exit code 0 with no exception.

- [ ] **Step 4: Record the facts used by every narrative document**

Use this exact baseline:

```text
Branch: main
Verification date: 2026-06-30
Backend tests: 202 passed
Ruff: clean
Frontend: production build passed
OpenAPI paths: 32
Catalog fixtures: 5 schemas and 5 templates
Real-world UIR dataset: 16 documents
Real-world import/execution/package verification: 16/16
Real-world strict validation: procurement 5/5; other tracked domains 0/11
Real-world mapping recall: 0.4259
Real-world mapping badcase violations: 0
Procurement required coverage: 1.000 versus generic 0.333
Content retrieval Recall@3: 1.000
Knowledge loop: old snapshot unchanged and zero badcase violations
LLM fallback: zero auto-accepted suggestions and secret redaction passed
```

Do not commit in this task; these facts are inputs to the following edits.

### Task 2: Rewrite The Project Entry Point And Final Handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/final_handoff_status.md`

- [ ] **Step 1: Replace the README status narrative**

Keep `# SchemaPack Agent`, then organize the document under these headings:

```markdown
## Current Status
## Implemented Capabilities
## Verified Evidence
## Quick Start
## Unified Verification
## Documentation Map
## Production Boundaries
```

The current-status block must state:

```markdown
Current verified baseline (2026-06-30): `main`, 202 backend tests,
Ruff clean, frontend production build successful, and 32 exported OpenAPI paths.
```

The evidence block must distinguish:

- 16/16 real-world documents import, execute, and produce verifier-passing packages;
- strict validation passes for five procurement samples, while the other 11
  samples remain review-required and are not claimed as field-valid;
- procurement required coverage is 1.000 versus 0.333 for the generic schema;
- the 32-query retrieval report records `Recall@3 = 1.000`;
- both knowledge-loop reports preserve snapshots and record zero badcase violations.

Use links to detailed documents instead of copying the 32-path API inventory.

- [ ] **Step 2: Rewrite the final handoff as the authoritative status document**

Use these headings:

```markdown
# SchemaPack Agent Final Handoff Status
## Integrated Repository State
## Implemented Capability Matrix
## API And Frontend Surface
## Catalogs, Data, And Packages
## Evaluation Evidence
## Reproduction Commands
## Known Boundaries
## Productionization Directions
## Final Verification On 2026-06-30
```

Include the current branch, verification baseline, five catalog types, 16
real-world documents, report paths, honest strict-validation split, and exact
PowerShell commands. Remove references to removed worktrees and superseded
branch-specific delivery state.

- [ ] **Step 3: Scan both documents for stale state**

Run:

```powershell
rg -n "codex/guideline-2026-06-29|160 passed|Final Verification On 2026-06-29" README.md docs\final_handoff_status.md
```

Expected: no matches.

- [ ] **Step 4: Check Markdown whitespace and commit**

Run:

```powershell
git diff --check -- README.md docs\final_handoff_status.md
git add README.md docs\final_handoff_status.md
git commit -m "docs: refresh project status and handoff"
```

Expected: a documentation-only commit.

### Task 3: Align Developer, API, And Deployment Guides

**Files:**
- Modify: `docs/developer_guide.md`
- Modify: `docs/api_usage_examples.md`
- Modify: `docs/deployment.md`

- [ ] **Step 1: Update the developer guide around current ownership boundaries**

Document this pipeline exactly:

```text
UIR -> Schema/Template Snapshot -> Candidate Extraction -> Mapping
-> Transform -> Canonical Model -> Render -> Content Organization
-> Validation -> Manifest -> ZIP -> Package Verification
```

Describe:

- `backend/app/services/task_execution_service.py` as pipeline orchestration;
- schema/template catalog governance and immutable task snapshots;
- review-derived knowledge candidates and active-pack effective templates;
- `scripts/verify_all.py --check-openapi` as the default local gate;
- report regeneration commands for production-like, real-world, retrieval,
  knowledge-loop, and LLM fallback evidence;
- common issues for `.env`, SQLite state, frontend dependencies, and occupied
  API ports.

- [ ] **Step 2: Update API examples to match the 32-path OpenAPI surface**

Keep representative workflows rather than listing every operation:

1. health;
2. schema/template catalog reads and version transitions;
3. UIR import;
4. task create and execute;
5. report and package retrieval;
6. review approval/rejection;
7. candidate acceptance and pack activation;
8. evaluation-report reads;
9. audit log reads.

Use current paths from `docs/openapi.json`, including:

```text
POST /api/v1/tasks/{task_id}/execute
GET  /api/v1/tasks/{task_id}/reports/{report_name}
GET  /api/v1/evaluation-reports/{report_id}
POST /api/v1/knowledge/packs/{pack_id}/activate
GET  /api/v1/audit-logs
```

Do not document phase10-only replay, convert, or legacy mapping endpoints because
they are historical and not present in current OpenAPI.

- [ ] **Step 3: Update deployment instructions**

Document:

- local backend and frontend commands;
- Docker Compose commands;
- SQLite and storage volume locations;
- `.env.example` and `.env.production.example`;
- optional API-key authentication;
- optional LLM modes and the default-disabled boundary;
- the absence of built-in TLS termination, SSO, tenancy, and managed secrets.

- [ ] **Step 4: Verify paths and commit**

Run:

```powershell
$api = Get-Content -Raw -Encoding UTF8 docs\openapi.json | ConvertFrom-Json
$required = @(
  '/api/v1/tasks/{task_id}/execute',
  '/api/v1/tasks/{task_id}/reports/{report_name}',
  '/api/v1/evaluation-reports/{report_id}',
  '/api/v1/knowledge/packs/{pack_id}/activate',
  '/api/v1/audit-logs'
)
foreach ($path in $required) {
  if (-not $api.paths.PSObject.Properties.Name.Contains($path)) {
    throw "Missing OpenAPI path: $path"
  }
}
git diff --check -- docs\developer_guide.md docs\api_usage_examples.md docs\deployment.md
git add docs\developer_guide.md docs\api_usage_examples.md docs\deployment.md
git commit -m "docs: align developer api and deployment guides"
```

Expected: all required paths exist and the commit succeeds.

### Task 4: Align Demo, Requirements, Package, And Dataset Guides

**Files:**
- Modify: `docs/final_demo_script.md`
- Modify: `docs/requirement_mapping.md`
- Modify: `docs/package_spec.md`
- Modify: `docs/real_world_uir_dataset.md`

- [ ] **Step 1: Update the final demo script**

Use a reviewer-friendly sequence:

1. run the unified verification gate;
2. start backend and frontend;
3. import a real procurement UIR;
4. create and execute a task;
5. inspect mapping evidence, validation, content organization, and package;
6. demonstrate review-to-knowledge-pack activation;
7. show the four deepening reports;
8. explain strict-validation and production boundaries.

Every command must be runnable from `F:\p2` in PowerShell.

- [ ] **Step 2: Update Topic 5 requirement mapping**

Map each requirement to current evidence:

| Requirement | Current implementation | Evidence |
| --- | --- | --- |
| standardization | schema/template snapshots, mapping, transform, canonical output | package and mapping reports |
| intelligent organization | summaries, tags, protected chunks, source links | retrieval report |
| specialized conversion | five catalogs including procurement | procurement comparison report |
| evaluation | production-like and 16-document real-world runs | committed report pairs |
| continuous improvement | review candidates, packs, effective templates | both knowledge-loop reports |
| safety and traceability | evidence, confidence, badcases, audit logs, immutable snapshots | API and report evidence |

Keep OCR, full RAG/vector search, model training, and enterprise identity outside
the implemented boundary.

- [ ] **Step 3: Update the package specification**

Describe the current required package artifacts, manifest hashes, schema/template
snapshot references, source-linked chunks, validation/content-organization
reports, and strict verifier checks. State that package verification proves
structural integrity and traceability; it does not imply every target field
passed strict semantic validation.

- [ ] **Step 4: Update the real-world dataset guide**

Record this distribution:

```text
general_doc: 3
meeting_doc: 3
policy_doc: 5
procurement_doc: 5
total: 16
```

Record:

- source manifest and cached-source workflow;
- deterministic extraction/validation commands;
- 16 source-backed mapping rows and 32 retrieval queries;
- 16/16 import, execution, and package verification;
- strict validation currently passing for procurement 5/5 and failing for the
  other 11 due to review-required/unmapped fields;
- dataset and evaluator limitations.

- [ ] **Step 5: Verify metrics against reports and commit**

Run:

```powershell
$real = Get-Content -Raw -Encoding UTF8 reports\real_world_eval_report.json | ConvertFrom-Json
$mapping = Get-Content -Raw -Encoding UTF8 reports\real_world_mapping_eval_report.json | ConvertFrom-Json
$proc = Get-Content -Raw -Encoding UTF8 reports\procurement_doc_eval_report.json | ConvertFrom-Json
$retrieval = Get-Content -Raw -Encoding UTF8 reports\content_organization_retrieval_eval.json | ConvertFrom-Json
if ($real.dataset_size -ne 16) { throw 'Unexpected dataset size' }
if ($real.package_verify_pass_count -ne 16) { throw 'Unexpected package pass count' }
if ($mapping.summary.badcase_violation_count -ne 0) { throw 'Unexpected badcase violation' }
if ($proc.procurement_doc.required_coverage -ne 1.0) { throw 'Unexpected procurement coverage' }
if ($retrieval.summary.'Recall@3' -ne 1.0) { throw 'Unexpected Recall@3' }
git diff --check -- docs\final_demo_script.md docs\requirement_mapping.md docs\package_spec.md docs\real_world_uir_dataset.md
git add docs\final_demo_script.md docs\requirement_mapping.md docs\package_spec.md docs\real_world_uir_dataset.md
git commit -m "docs: align demo requirements package and dataset guides"
```

Expected: all metric assertions and the commit succeed.

### Task 5: Regenerate Acceptance Evidence

**Files:**
- Modify: `docs/acceptance_report.md`
- Modify: `reports/acceptance_report.json`
- Modify: `reports/acceptance_report.md`

- [ ] **Step 1: Regenerate the acceptance report**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\build_acceptance_report.py
```

Expected:

```text
reports/acceptance_report.json
reports/acceptance_report.md
docs/acceptance_report.md
```

- [ ] **Step 2: Confirm report copies agree**

Run:

```powershell
$docsHash = (Get-FileHash docs\acceptance_report.md -Algorithm SHA256).Hash
$reportHash = (Get-FileHash reports\acceptance_report.md -Algorithm SHA256).Hash
if ($docsHash -ne $reportHash) { throw 'Acceptance Markdown copies differ' }
$report = Get-Content -Raw -Encoding UTF8 reports\acceptance_report.json | ConvertFrom-Json
if ($report.project -ne 'SchemaPack Agent') { throw 'Unexpected acceptance project' }
if ($report.pipeline -notmatch 'UIR') { throw 'Acceptance pipeline is missing' }
```

Expected: exit code 0.

- [ ] **Step 3: Commit regenerated evidence**

Run:

```powershell
git diff --check -- docs\acceptance_report.md reports\acceptance_report.json reports\acceptance_report.md
git add docs\acceptance_report.md reports\acceptance_report.json reports\acceptance_report.md
git commit -m "docs: regenerate current acceptance evidence"
```

Expected: a generated-evidence commit.

### Task 6: Run Final Documentation And Project Verification

**Files:**
- Verify: `README.md`
- Verify: `docs/final_handoff_status.md`
- Verify: `docs/developer_guide.md`
- Verify: `docs/api_usage_examples.md`
- Verify: `docs/deployment.md`
- Verify: `docs/final_demo_script.md`
- Verify: `docs/requirement_mapping.md`
- Verify: `docs/package_spec.md`
- Verify: `docs/real_world_uir_dataset.md`
- Verify: `docs/acceptance_report.md`
- Verify: `reports/acceptance_report.json`
- Verify: `reports/acceptance_report.md`

- [ ] **Step 1: Scan canonical documents for superseded state**

Run:

```powershell
$canonical = @(
  'README.md',
  'docs/final_handoff_status.md',
  'docs/developer_guide.md',
  'docs/api_usage_examples.md',
  'docs/deployment.md',
  'docs/final_demo_script.md',
  'docs/requirement_mapping.md',
  'docs/package_spec.md',
  'docs/real_world_uir_dataset.md'
)
rg -n "codex/guideline-2026-06-29|160 passed|Final Verification On 2026-06-29" $canonical
if ($LASTEXITCODE -eq 0) { throw 'Superseded project state remains in canonical docs' }
```

Expected: no matches.

- [ ] **Step 2: Verify every required current fact is documented**

Run:

```powershell
$handoff = Get-Content -Raw -Encoding UTF8 docs\final_handoff_status.md
foreach ($marker in @('main', '202 passed', '32', '16/16', '2026-06-30')) {
  if (-not $handoff.Contains($marker)) { throw "Missing handoff marker: $marker" }
}
$readme = Get-Content -Raw -Encoding UTF8 README.md
foreach ($marker in @('202 passed', '32 exported OpenAPI paths', '16/16')) {
  if (-not $readme.Contains($marker)) { throw "Missing README marker: $marker" }
}
```

Expected: exit code 0.

- [ ] **Step 3: Run full project verification**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Expected:

```text
202 passed
All checks passed!
✓ built
exported 32 paths
```

- [ ] **Step 4: Check the final diff and repository state**

Run:

```powershell
git diff --check HEAD~4..HEAD
git status --short --branch
git log -5 --oneline --decorate
```

Expected: `## main` with no uncommitted files and four focused documentation
commits after the plan commit.
