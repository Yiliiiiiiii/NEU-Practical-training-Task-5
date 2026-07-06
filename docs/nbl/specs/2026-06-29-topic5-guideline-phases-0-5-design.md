# SchemaPack Agent Topic 5 Phases 0–5 Design

> **Historical specification:** Preserved for design rationale. See [`../../project_status.md`](../../交接/project_status.md) for current implementation status.

## 1. Purpose

Implement all required and optional items in
`docs/guildline/2026.-6-29.md` while preserving the production boundary and
the existing conversion chain:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP
```

The work must produce reproducible evidence, dedicated procurement mapping,
a human-gated real-world knowledge loop, deterministic chunk retrieval
evaluation, frontend evidence panels, and safe LLM fallback evaluation.

## 2. Scope and Constraints

### In scope

- Phase 0 through Phase 5 from the guideline.
- A prerequisite repair for clean-checkout database initialization in tests.
- A prerequisite repair for reproducible frontend dependency installation.
- Additive API/report access needed by the evidence panels.
- JSON and Markdown output for every new evaluation script.
- Documentation and final handoff updates.

### Out of scope

- Production PDF, Office, image, scan, or OCR parsing.
- Full RAG or a vector database.
- Model training.
- Autonomous LLM mapping acceptance.
- Cleaning, normalization, entity linking, or unrelated topic capabilities.
- Breaking changes to existing API routes, report names, or package files.

## 3. Chosen Approach

Use a strict sequential implementation that reuses current production
services. Each phase starts with a failing test, adds the smallest necessary
implementation, generates its reports, passes phase verification, and is
committed before the next phase begins.

This approach is preferred over:

1. Reimplementing mapping, chunking, and knowledge logic inside standalone
   scripts, which would be faster initially but could drift from production.
2. Refactoring the project into a generalized evaluation platform first,
   which would increase the blast radius and violate the guideline's
   convergence requirement.

Shared helpers may be extracted only when two or more phase scripts need the
same deterministic report or metric behavior.

## 4. Architecture

### 4.1 Evaluation scripts

Each new script exposes importable functions for tests and a small CLI entry
point. Scripts resolve paths relative to a configurable repository root, use
UTF-8, avoid network access by default, and always attempt to write both JSON
and Markdown reports.

Missing optional inputs produce a structured entry:

```json
{
  "status": "missing",
  "reason": "report file not found",
  "recommended_command": "..."
}
```

Missing required fixtures produce a clear failed check in the report and a
non-zero CLI exit after report generation. Malformed inputs produce an
actionable error naming the path and validation problem.

### 4.2 Production service reuse

- Procurement fixtures are loaded by the existing schema/template services
  and seeded through `CatalogGovernanceService`.
- Knowledge-loop evaluation uses the existing mapping, review, candidate,
  knowledge-pack, effective-template, task, and package services with an
  isolated temporary SQLite database and storage root.
- Retrieval evaluation uses `ChunkOrganizerService` to generate each strategy's
  chunks, then applies a deterministic standard-library scorer.
- LLM evaluation uses existing disabled, stub, and OpenAI-compatible adapters.
  Network access requires an explicit CLI flag.

### 4.3 Frontend report access

Existing endpoints remain compatible. Additive report reads expose:

- a task package manifest through the existing task-report pattern;
- the generated real-world knowledge-loop report through a read-only
  evaluation-report endpoint.

Absence of a generated knowledge-loop report returns a typed unavailable state
rather than a fabricated metric set.

## 5. Phase Design

### 5.1 Prerequisite reproducibility repairs

The governance security tests currently depend on an already initialized
working-directory SQLite file. Test application setup will explicitly bind and
initialize the temporary database it declares, eliminating hidden state.

Frontend dependencies currently use invalid ranges such as `^latest`.
Dependencies will be pinned to compatible concrete ranges and a lock file will
be generated. Clean installation and production build become verifiable from a
new worktree.

### 5.2 Phase 0: Acceptance evidence loop

`scripts/build_acceptance_report.py` reads known reports and documentation,
normalizes their core metrics, and writes:

- `reports/acceptance_report.json`
- `reports/acceptance_report.md`
- `docs/交接/acceptance_report.md`

The Markdown document follows the fourteen guideline sections and distinguishes
observed evidence, missing evidence, boundaries, and recommended reproduction
commands. It never converts missing evidence into a pass.

### 5.3 Phase 1: Procurement schema and template

Add `procurement_doc_v1.json` and `procurement_doc_base_v1.json` following
existing fixture shapes. All aliases, regex targets, enum maps, defaults, and
transforms must refer to declared schema fields.

Procurement mapping will:

- distinguish budget and award amounts;
- retain multiple-amount ambiguity for review;
- keep contact phone optional;
- default currency only under existing transform semantics;
- map notice and procurement-method values through explicit enum maps.

`eval_real_world_uir.py` selects the procurement schema/template explicitly.
Missing procurement fixtures cause a visible error or declared degradation in
the report; they never silently select `general_doc`.

### 5.4 Phase 2: Real-world knowledge loop

The evaluator runs the same real-world sample set twice:

1. baseline with the base template;
2. after fixture-driven review decisions, accepted candidates, draft-pack
   creation, explicit activation, and effective-template resolution.

Only decisions marked `approve` can enter a pack. Rejected and badcase-blocked
aliases remain inactive. The report records baseline, decisions, activated
aliases, after metrics, remaining ambiguity, badcase violations, and immutable
pre-activation task snapshots.

The evaluation uses isolated database/storage paths so repeated runs do not
pollute the developer database.

### 5.5 Phase 3: Chunk retrieval evaluation

For the same UIR documents and queries, generate chunks with:

- `fixed_window`
- `heading_aware`
- `source_block_aware`
- `table_protect`
- `parent_child`

The scorer tokenizes Latin terms and Chinese character n-grams, scores chunk
text plus summary, keywords, and title path, and applies a deterministic boost
for expected terms. Relevance is determined from intersections between
`source_block_ids` and query `expected_block_ids`.

The report includes Recall@1/3/5, MRR, nDCG@5, source-link coverage,
table-chunk integrity, average token estimate, and chunk count. If an advanced
strategy does not beat the baseline, the report records the actual result and
failure analysis.

### 5.6 Phase 4: Frontend evidence chain

Split focused presentation components from `App.tsx`:

- `MappingEvidencePanel`
- `ValidationIssuePanel`
- `ChunkEvidencePanel`
- `PackageManifestPanel`
- `KnowledgeComparisonPanel`

The panels retain the current workflow and styling conventions. They provide:

- complete mapping evidence with visible low-confidence rows and expandable
  JSON;
- validation issues grouped by type and severity with deterministic suggested
  actions;
- chunk strategy/table/quality filters and parent-child relationships;
- manifest file status, required flags, sizes, media types, and expandable
  SHA-256 values;
- knowledge before/after metrics or an explicit not-run state with the command
  to generate the report.

Data normalization and filter behavior are extracted into pure functions and
covered by lightweight Vitest tests. No large UI framework is introduced.

### 5.7 Phase 5: Optional LLM fallback evaluation

The default evaluator covers `disabled` and `stub` without credentials or
network access. OpenAI-compatible mode runs only with `--allow-network` and
configured environment credentials.

The report proves:

- no suggestion is auto-accepted;
- suggestions remain review-required;
- badcase filtering still applies;
- secret-looking values are redacted;
- non-strict provider errors become warnings;
- strict provider errors fail the task;
- provider errors do not break deterministic conversion in non-strict mode.

Secrets, prompts, and raw provider responses are not written to reports.

## 6. Data Flow

```text
Versioned fixtures and real-world UIR
  -> existing conversion and governance services
  -> generated packages and phase metrics
  -> JSON/Markdown evaluation reports
  -> acceptance report aggregation
  -> read-only frontend evidence panels
```

Knowledge changes apply only to tasks created after active-pack resolution.
Historical task snapshots and packages remain unchanged.

## 7. Testing Strategy

Use test-driven development for behavior changes:

1. Add one failing test for the next behavior.
2. Confirm the expected failure.
3. Implement the minimum change.
4. Run the focused test.
5. Run the phase suite.

Required new backend tests:

- acceptance report generation and missing inputs;
- procurement fixture validity and mapping ambiguity;
- knowledge approve/reject/activation/badcase/snapshot behavior;
- retrieval scoring and empty inputs;
- LLM disabled/stub/redaction/strictness/report behavior;
- additive manifest and evaluation-report reads.

Frontend tests cover evidence normalization, filters, suggested actions, and
empty knowledge-report state. The production build remains the final frontend
gate.

After every phase:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..\frontend
npm test -- --run
npm run build
```

Final verification also runs:

```powershell
python scripts\verify_all.py --check-openapi
python scripts\eval_production_like.py
python scripts\build_acceptance_report.py
python scripts\eval_real_world_knowledge_loop.py
python scripts\eval_chunk_retrieval.py
python scripts\eval_llm_fallback_modes.py --mode stub
```

Real-world HTTP evaluation is run with a temporary local backend and its
results are recorded honestly.

## 8. Documentation and Delivery

Update the developer guide, dataset guide, final handoff status, requirement
mapping, OpenAPI snapshot, and acceptance report. Generated phase reports are
committed only where the repository's report allowlist permits them.

The final handoff states:

- commands executed and their exit status;
- exact report paths;
- metric summaries;
- retained badcases and limitations;
- whether optional network LLM evaluation was skipped.

## 9. Acceptance Criteria

The implementation is accepted when:

- all Phase 0–5 deliverables in the guideline exist or an explicitly optional
  artifact is documented as not run;
- procurement real-world samples use the dedicated catalog;
- all new reports contain real measurements, not fabricated improvements;
- badcase violations and LLM auto-acceptance are zero;
- package verification and downstream smoke ingestion pass;
- frontend evidence panels render all required states;
- clean backend tests, Ruff, frontend tests, frontend build, production-like
  evaluation, and `verify_all.py --check-openapi` pass;
- the production input boundary remains UIR.
