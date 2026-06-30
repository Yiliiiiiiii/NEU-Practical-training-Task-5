# Current Project Documentation Refresh Design

## Goal

Refresh the canonical project documentation so that acceptance reviewers and
future developers see the behavior, evidence, commands, and boundaries of the
current `main` branch rather than historical worktree or branch state.

## Audience

The documentation serves two primary audiences:

- acceptance and demonstration reviewers who need a concise capability map,
  reproducible evidence, and honest boundaries;
- developers and operators who need accurate setup, API, evaluation,
  deployment, extension, and troubleshooting instructions.

The top-level README provides the shared entry point. Topic-specific documents
then avoid repeating full project status narratives.

## Source Of Truth

Documentation facts are derived from current repository artifacts:

- Git state: `main` is the integrated branch and `F:\p2` is the sole worktree;
- verification: `scripts/verify_all.py --check-openapi` runs backend Pytest,
  Ruff, the frontend production build, and OpenAPI export;
- verified baseline on 2026-06-30: 202 backend tests, Ruff clean, frontend build
  successful, and 32 exported OpenAPI paths;
- catalog fixtures: five schemas and five mapping templates under
  `examples/production_like/`;
- real-world dataset: 16 tracked UIR documents across general, meeting, policy,
  and procurement document types;
- evaluation evidence: committed JSON/Markdown report pairs under `reports/`;
- API inventory: `docs/openapi.json`;
- runtime and deployment behavior: application settings, Dockerfiles,
  `docker-compose.yml`, and executable scripts.

Generated reports remain evidence artifacts. Narrative documentation summarizes
their conclusions without silently changing report data.

## Documentation Architecture

### README

`README.md` becomes the concise project entry point:

- project purpose and current status;
- implemented pipeline and governance capabilities;
- reproduced evidence highlights;
- quick-start and unified verification commands;
- links to detailed documentation;
- explicit production boundaries.

It must not contain stale branch/worktree references or duplicate every API and
evaluation detail.

### Final Handoff

`docs/final_handoff_status.md` becomes the authoritative current-state handoff:

- integrated branch and verification baseline;
- implemented capabilities by subsystem;
- current evaluation results, including limitations visible in reports;
- reproducible commands;
- known non-goals and productionization directions.

Historical statements about the removed
`codex/guideline-2026-06-29` worktree and the old 160-test baseline are removed.

### Developer And Operator Guides

- `docs/developer_guide.md` documents repository structure, pipeline ownership,
  extension points, governance rules, and verification.
- `docs/api_usage_examples.md` covers the current 32-path API surface through
  representative workflows rather than duplicating the whole OpenAPI document.
- `docs/deployment.md` documents local and Docker Compose deployment,
  persistence, environment profiles, and production boundaries.
- `docs/final_demo_script.md` provides a reproducible reviewer-oriented demo
  sequence based on current commands and reports.

### Acceptance And Domain Guides

- `docs/requirement_mapping.md` maps Topic 5 requirements to current code,
  APIs, datasets, and evidence.
- `docs/package_spec.md` describes the package contract and verifier behavior.
- `docs/real_world_uir_dataset.md` records the current 16-document distribution,
  source/reproduction flow, evaluation labels, and limitations.
- `docs/acceptance_report.md` remains generated acceptance evidence; it is
  regenerated from current report inputs instead of manually rewritten.

### Historical Material

The following remain historical or source artifacts and are not normalized into
current-state documentation:

- `docs/guildline/`;
- `docs/superpowers/plans/` and prior design specifications;
- `docs/nbl/`;
- timestamped JSON/Markdown evaluation reports.

They may be linked when useful, but current documentation must not present their
branch names or historical test counts as present state.

## Content Rules

- Use current commands that work from PowerShell on Windows.
- State measured values with their verification date.
- Distinguish package verification success from field-level validation success.
- State that real-world import, execution, and package verification are 16/16,
  while only procurement samples currently pass strict field validation in the
  committed real-world report.
- State mapping and retrieval metrics exactly as recorded in current reports.
- Describe LLM fallback as optional, disabled by default, review-only, and
  network-gated.
- Do not claim OCR, full RAG/vector search, model training, tenant isolation,
  SSO, or enterprise authorization.
- Prefer links to `docs/openapi.json` and reports over copied long inventories.

## Files To Update

- `README.md`
- `docs/final_handoff_status.md`
- `docs/developer_guide.md`
- `docs/api_usage_examples.md`
- `docs/deployment.md`
- `docs/final_demo_script.md`
- `docs/requirement_mapping.md`
- `docs/package_spec.md`
- `docs/real_world_uir_dataset.md`
- generated `docs/acceptance_report.md`
- generated `reports/acceptance_report.json`
- generated `reports/acceptance_report.md`

No application behavior or API contract changes are included.

## Validation

The refresh is accepted when:

1. `scripts/verify_all.py --check-openapi` succeeds;
2. `docs/openapi.json` still contains 32 paths;
3. the catalog contains five schemas and five templates;
4. the tracked real-world dataset contains 16 non-rejected UIR JSON files;
5. canonical documentation contains no removed worktree reference, old
   `160 passed` statement, or old final-verification heading;
6. report-derived metrics in narrative documents match the committed JSON;
7. Markdown links and referenced local commands point to existing files.

## Delivery

Documentation changes are committed on `main` as a focused documentation
refresh. Historical branches and evidence reports remain traceable through Git.
