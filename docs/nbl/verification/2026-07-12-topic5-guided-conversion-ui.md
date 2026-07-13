# Topic 5 Guided Conversion Studio Verification

Initial verification: 2026-07-12
Responsive completion: 2026-07-13
Health and operational-state revalidation: 2026-07-13

Target branch: `feat/topic5-guided-conversion-ui`

Prior verification-report commit: `f1c46cd8`.

Visual-acceptance branch baseline: `2bc99187`. This identifies the code used
for the local browser evidence below; it is not a claim that this is the final
merged tip or that all later fixes have been reverified.

Final verification source tip: `d16d2fa86981bbbab8ce8e29c72ba9edd398cf57`
(immediately before this report's result-metadata update). It includes the
External UIR invalidation and Evidence stale-request fixes in addition to the
visual-acceptance changes.

## Scope And Runtime

Frontend dependencies were installed from the committed lockfile with `npm ci`.
The worktree has no `backend\.venv\Scripts\python.exe`; the host Python had the
documented runtime dependencies available: FastAPI 0.115.6, Uvicorn 0.34.0,
and PyYAML 6.0.2. The backend was started with:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/health` returned `200 {"status":"ok"}`. The frontend
was started on a free local port with:

```powershell
Push-Location frontend
npm run dev -- --port 5174 --strictPort
Pop-Location
```

The Vite `/api` and `/health` proxies sent the browser's same-origin requests
to the local backend. The browser-origin check
`http://127.0.0.1:5174/health` returned `200 {"status":"ok"}`, and each fresh
Overview snapshot reported `后端状态：已连接`. No route or browser-network mocking
was used. The supplemental pagination data described below was created only in
this worktree's ignored local database and storage.

Playwright prerequisite: `npx` resolved to
`E:\Program Files\nodejs\npx.ps1`.

The bundled wrapper exists at
`C:\Users\31338\.codex\skills\playwright\scripts\playwright_cli.sh`, but
this Windows environment provides WSL Bash rather than Git Bash and could not
execute its Windows path. The wrapper's exact command,
`npx --yes --package @playwright/cli playwright-cli`, was used as the
Windows-compatible equivalent. Every interactive target came from the
immediately preceding browser snapshot.

## Real Flow Result

The original 1440x1024 evidence was retained from the preceding real run,
which created `task_ea27771ee5a7` in `review_required`.

For the responsive completion, a new real conversion completed through
Sample -> validate UIR -> import UIR -> choose
`policy_doc / policy_doc_base_v1` -> configure -> run. It created
`task_3937000fa803`, which ended in `review_required`. Its Task Overview
reported Validation passed and Package verifier passed; the Mapping tab kept
one low-confidence candidate in the Review queue. The responsive execution,
task-detail, Tasks, and Review screenshots below are from that task.

For the operational-state revalidation, an isolated local UIR was imported as
`qa_evidence_seed_001`, then 101 local tasks were created. The executed seed
task, `task_d3874ae49803`, ended in `review_required` with its package verifier
passed. These temporary local records exercise pagination and evidence loading;
they are not product acceptance data and are not committed.

## Commands And Results

```powershell
Push-Location frontend
npm ci
npm test
npm run build
Pop-Location
```

The health and operational-state revalidation reran the frontend test and
build commands. Their branch-baseline results remain in the self-review section
for traceability; the final merged-tip verification is recorded below.

The README's documented repository gate is:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

`backend\.venv\Scripts\python.exe` is absent in this isolated worktree. The
same Python runtime from the primary workspace was invoked against this clean
integration worktree:

```powershell
F:\p2\backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Final result: PASS. `1229` backend tests passed, Ruff passed, the frontend
production build passed, and OpenAPI export completed with `65` paths. The
command completed successfully in the clean integration worktree; no backend
or OpenAPI source file changed.

## Screenshot Inventory

All 46 artifacts are real browser screenshots in
`output/playwright/topic5-guided-conversion-ui/`. Files 1-45 are viewport
captures; file 46 is a full-page capture taken after setting the viewport to
1280x900. Coverage is stated exactly:

| Primary view | 1440x1024 | 1280x900 | 1024x768 |
| --- | --- | --- | --- |
| Overview | 1, 44 | 42 | 43 |
| Conversion Step 1 | 2 | 18 | 19 |
| Conversion Step 2 | 3 | 20 | 21 |
| Conversion Step 3 | 4 | 22 | 23 |
| Conversion Step 4 | 5 | 24 | 25 |
| Execution | 6 | 26 | 27 |
| Task Overview | 7 | 28 | 29 |
| Task Mapping | 8 | 30 | 31 |
| Task Package | 9 | 32 | 33 |
| Tasks | 10 | 34 | 35 |
| Review queue | — | 36 | 37 |
| SchemaPacks | 11 | 38 | 39 |
| Evidence | 12 | 40, 45 | 41 |

Overview now has evidence at all three responsive widths, with file 44 adding
an explicit post-health 1440x1024 capture. All named primary views have all
three widths except Review queue, which is captured only at 1280x900 and
1024x768. Files 13-17 remain earlier supplemental responsive captures; file
46 is supplemental task-detail audit pagination evidence.

| # | View | Viewport | Artifact |
| --- | --- | --- | --- |
| 1 | Overview | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/01-overview-1440x1024.png` |
| 2 | Conversion Step 1 (Sample) | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/02-conversion-step1-sample-1440x1024.png` |
| 3 | Conversion Step 2 | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/03-conversion-step2-1440x1024.png` |
| 4 | Conversion Step 3 | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/04-conversion-step3-1440x1024.png` |
| 5 | Conversion Step 4 | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/05-conversion-step4-1440x1024.png` |
| 6 | Execution | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/06-execution-1440x1024.png` |
| 7 | Task Overview | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/07-task-overview-1440x1024.png` |
| 8 | Task Mapping | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/08-task-mapping-1440x1024.png` |
| 9 | Task Package | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/09-task-package-1440x1024.png` |
| 10 | Tasks | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/10-tasks-1440x1024.png` |
| 11 | SchemaPacks | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/11-schemapacks-1440x1024.png` |
| 12 | Evidence | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/12-evidence-1440x1024.png` |
| 13 | Review queue (earlier supplemental) | 1280x900 | `output/playwright/topic5-guided-conversion-ui/13-review-1280x900.png` |
| 14 | Task Mapping (earlier supplemental) | 1280x900 | `output/playwright/topic5-guided-conversion-ui/14-task-mapping-1280x900.png` |
| 15 | Task Mapping (earlier supplemental) | 1024x768 | `output/playwright/topic5-guided-conversion-ui/15-task-mapping-1024x768.png` |
| 16 | Conversion Step 1 (earlier supplemental) | 1024x768 | `output/playwright/topic5-guided-conversion-ui/16-conversion-step1-1024x768.png` |
| 17 | SchemaPacks (earlier supplemental) | 1024x768 | `output/playwright/topic5-guided-conversion-ui/17-schemapacks-1024x768.png` |
| 18 | Conversion Step 1 (validated Sample UIR) | 1280x900 | `output/playwright/topic5-guided-conversion-ui/18-conversion-step1-1280x900.png` |
| 19 | Conversion Step 1 (validated Sample UIR) | 1024x768 | `output/playwright/topic5-guided-conversion-ui/19-conversion-step1-1024x768.png` |
| 20 | Conversion Step 2 | 1280x900 | `output/playwright/topic5-guided-conversion-ui/20-conversion-step2-1280x900.png` |
| 21 | Conversion Step 2 | 1024x768 | `output/playwright/topic5-guided-conversion-ui/21-conversion-step2-1024x768.png` |
| 22 | Conversion Step 3 | 1280x900 | `output/playwright/topic5-guided-conversion-ui/22-conversion-step3-1280x900.png` |
| 23 | Conversion Step 3 | 1024x768 | `output/playwright/topic5-guided-conversion-ui/23-conversion-step3-1024x768.png` |
| 24 | Conversion Step 4 | 1280x900 | `output/playwright/topic5-guided-conversion-ui/24-conversion-step4-1280x900.png` |
| 25 | Conversion Step 4 | 1024x768 | `output/playwright/topic5-guided-conversion-ui/25-conversion-step4-1024x768.png` |
| 26 | Execution | 1280x900 | `output/playwright/topic5-guided-conversion-ui/26-execution-1280x900.png` |
| 27 | Execution | 1024x768 | `output/playwright/topic5-guided-conversion-ui/27-execution-1024x768.png` |
| 28 | Task Overview | 1280x900 | `output/playwright/topic5-guided-conversion-ui/28-task-overview-1280x900.png` |
| 29 | Task Overview | 1024x768 | `output/playwright/topic5-guided-conversion-ui/29-task-overview-1024x768.png` |
| 30 | Task Mapping | 1280x900 | `output/playwright/topic5-guided-conversion-ui/30-task-mapping-1280x900.png` |
| 31 | Task Mapping | 1024x768 | `output/playwright/topic5-guided-conversion-ui/31-task-mapping-1024x768.png` |
| 32 | Task Package | 1280x900 | `output/playwright/topic5-guided-conversion-ui/32-task-package-1280x900.png` |
| 33 | Task Package | 1024x768 | `output/playwright/topic5-guided-conversion-ui/33-task-package-1024x768.png` |
| 34 | Tasks | 1280x900 | `output/playwright/topic5-guided-conversion-ui/34-tasks-1280x900.png` |
| 35 | Tasks | 1024x768 | `output/playwright/topic5-guided-conversion-ui/35-tasks-1024x768.png` |
| 36 | Review queue | 1280x900 | `output/playwright/topic5-guided-conversion-ui/36-review-1280x900.png` |
| 37 | Review queue | 1024x768 | `output/playwright/topic5-guided-conversion-ui/37-review-1024x768.png` |
| 38 | SchemaPacks | 1280x900 | `output/playwright/topic5-guided-conversion-ui/38-schemapacks-1280x900.png` |
| 39 | SchemaPacks | 1024x768 | `output/playwright/topic5-guided-conversion-ui/39-schemapacks-1024x768.png` |
| 40 | Evidence | 1280x900 | `output/playwright/topic5-guided-conversion-ui/40-evidence-1280x900.png` |
| 41 | Evidence | 1024x768 | `output/playwright/topic5-guided-conversion-ui/41-evidence-1024x768.png` |
| 42 | Overview (connected health) | 1280x900 | `output/playwright/topic5-guided-conversion-ui/42-overview-1280x900.png` |
| 43 | Overview (connected health) | 1024x768 | `output/playwright/topic5-guided-conversion-ui/43-overview-1024x768.png` |
| 44 | Overview (connected health) | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/44-overview-health-1440x1024.png` |
| 45 | Evidence task selector and loaded reports | 1280x900 | `output/playwright/topic5-guided-conversion-ui/45-evidence-all-tasks-loaded-1280x900.png` |
| 46 | Task Detail Execution audit pagination (full page) | 1280x900 | `output/playwright/topic5-guided-conversion-ui/46-task-execution-audit-pagination-1280x900.png` |

## Visual And Accessibility Observations

- Overview is now revalidated at 1280x900, 1024x768, and 1440x1024 with the
  connected health state visibly resolved. The existing primary views retain
  their three-width coverage except Review queue, which remains correctly
  bounded to 1280x900 and 1024x768. The earlier responsive task state is
  `task_3937000fa803` / `review_required`.
- At 1024px, table-heavy Mapping and Package views keep their wide data inside
  their scrollable table regions; the application shell does not escape the
  viewport. Long hashes and the package path wrap within their cells.
- The 1024px workflow uses its narrow stacked layout and retains the sticky
  previous/next action footer above the viewport edge. Review retains its
  queue, evidence, impact, and available decision controls without overlap.
- One rendered defect was found and fixed: Evidence used the fixed-width
  `icon-button` class for a text-bearing refresh command. At 1024px that
  wrapped the Chinese label vertically. Removing that incorrect class in
  `frontend/src/components/EvaluationCenterPanel.tsx` restores the normal
  icon-plus-label command without changing any API contract.
- A real development-runtime defect was found and fixed: the new `api.health()`
  request uses `/health`, but Vite only proxied `/api`, so a browser with the
  default empty API base received Vite's 404 rather than the backend health
  response. `frontend/vite.config.ts` now proxies `/health` to the same local
  target. Direct backend and browser-origin health requests both returned 200,
  and the AppShell displayed `后端状态：已连接` in files 42-44. This changes no
  backend request or response contract.
- Evidence pagination was exercised with 101 isolated local tasks: the first
  API page returned 100 items and the second returned one. The Evidence
  selector contained the task beyond the first page, selected
  `task_d3874ae49803`, and loaded its mapping, validation, chunk, package, and
  lineage evidence; file 45 records the loaded report state.
- The same task had 102 local audit events. Execution first displayed `已显示
  100 / 共 102 条审计事件` and exposed `加载更多审计事件`; activating it produced
  `已显示 102 / 共 102 条审计事件`. File 46 preserves the pre-activation full-page
  state, including the summary and load-more control.

## Two-Stage Self Review

### 1. Coverage And Evidence Audit

PASS. `Get-ChildItem` counted exactly 46 PNG files in
`output/playwright/topic5-guided-conversion-ui/`, and every file is listed in
the inventory above. The matrix records Overview at all three widths and every
other named primary view at all three widths except Review queue, which is not
claimed at 1440x1024. The browser health snapshots and the isolated pagination
runtime state are recorded above, including the generated task's
`review_required` result.

### 2. Render And Change Audit

PASS. Inspected the fresh connected Overview captures at 1280x900, 1024x768,
and 1440x1024; the loaded Evidence capture; and the full-page Execution audit
pagination capture. The AppShell remained legible at all requested widths, and
the new evidence/audit controls reported their explicit text state without
overlap or shell escape. On the visual-acceptance branch baseline, full
`npm test` passed 21 files and 94 tests in 7.22 seconds; `npm run build`
completed in 2.62 seconds. On the final verification source tip, full
`npm test` passed 21 files and 98 tests in 6.02 seconds, and `npm run build`
passed in 2.54 seconds. The repository verification result is the passing gate
recorded above.

## Changed Files And API Contract

- Updated this report with the complete 46-file inventory, coverage matrix, and
  bounded health/pagination claims.
- Added five browser screenshot artifacts (`42` through `46`).
- Added the Vite `/health` proxy beside the existing `/api` proxy so the
  AppShell health probe reaches the real local backend; no backend API contract
  changed.
- Generated local runtime state (`frontend/node_modules`, `frontend/dist`,
  backend storage, logs, and Playwright session metadata) remains uncommitted.
