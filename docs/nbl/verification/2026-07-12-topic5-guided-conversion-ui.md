# Topic 5 Guided Conversion Studio Verification

Date: 2026-07-12

Branch: `codex/topic5-guided-conversion-ui-task7`

Baseline SHA: `2e591ea7036619659c06e209e696d73728ebcdb6`

## Scope And Runtime

Frontend dependencies were installed from the committed lockfile with `npm ci`.
The initial backend probe found no listener on `127.0.0.1:8000`. The documented
Uvicorn command initially failed because the host Python environment lacked
`PyYAML`; installing the exact documented requirement (`PyYAML==6.0.2`) allowed
the backend to start. The health check then returned `200 {"status":"ok"}`.

Frontend command (started for this verification and stopped afterward):

```powershell
npm run dev -- --port 5173
```

The final frontend used the repository Vite `/api` proxy to
`http://127.0.0.1:8000`. An explicit `VITE_API_BASE=http://127.0.0.1:8000`
was intentionally not retained because the local backend did not send an
`Access-Control-Allow-Origin` response for the Vite origin. The proxy path
allowed real API requests and was used for the screenshots and task run.

Playwright prerequisite: `npx` resolved to
`E:\Program Files\nodejs\npx.ps1`.

The bundled wrapper exists at
`C:\Users\31338\.codex\skills\playwright\scripts\playwright_cli.sh`, but
this Windows environment provides WSL Bash rather than Git Bash and could not
execute its Windows path. Exact fallback failure:

```text
wsl: Failed to translate 'D:\C\x86_64-12.2.0-release-posix-seh-msvcrt-rt_v10-rev2\mingw64\bin'
wsl: Failed to translate 'D:\MinGW\mingw64\bin'
/bin/bash: C:Users31338.codexskillsplaywrightscriptsplaywright_cli.sh: No such file or directory
```

The wrapper's exact command, `npx --yes --package @playwright/cli
playwright-cli`, was used as the Windows-compatible equivalent. Every
interactive target came from the immediately preceding browser snapshot.

## Real Flow Result

At 1440x1024, a real conversion was completed through Sample -> validate UIR
-> import UIR -> choose `policy_doc / policy_doc_base_v1` -> configure -> run.
It created `task_ea27771ee5a7`, which truthfully ended in
`review_required`. The task detail reported a passing Validation result and a
passing Package verifier; the generated mapping kept its low-confidence
candidate in the Review queue.

No fixture data, route mocks, or browser network mocking were used.

## Commands And Results

```powershell
Push-Location frontend
npm ci
npm test
npm run build
Pop-Location
```

Results:

- `npm test`: PASS, 16 files and 71 tests passed in 5.15 seconds.
- `npm run build`: PASS, TypeScript build and Vite production bundle completed
  in 2.55 seconds.

The README's documented repository gate is:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

`backend\.venv\Scripts\python.exe` is absent in this isolated worktree, so
the equivalent host-Python fallback was attempted:

```powershell
python scripts\verify_all.py --check-openapi
```

It did not complete before the 120-second tool limit. Exact outcome: process
timeout after 124.05 seconds, with no final pass/fail output available. This
verification is therefore **not claimed as passed**.

## Screenshot Inventory

All artifacts are real browser screenshots in
`output/playwright/topic5-guided-conversion-ui/`.

| View | Viewport | Artifact |
| --- | --- | --- |
| Overview | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/01-overview-1440x1024.png` |
| Conversion Step 1 (Sample) | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/02-conversion-step1-sample-1440x1024.png` |
| Conversion Step 2 | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/03-conversion-step2-1440x1024.png` |
| Conversion Step 3 | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/04-conversion-step3-1440x1024.png` |
| Conversion Step 4 | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/05-conversion-step4-1440x1024.png` |
| Execution | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/06-execution-1440x1024.png` |
| Task Overview | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/07-task-overview-1440x1024.png` |
| Task Mapping | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/08-task-mapping-1440x1024.png` |
| Task Package | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/09-task-package-1440x1024.png` |
| Tasks | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/10-tasks-1440x1024.png` |
| SchemaPacks | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/11-schemapacks-1440x1024.png` |
| Evidence | 1440x1024 | `output/playwright/topic5-guided-conversion-ui/12-evidence-1440x1024.png` |
| Review queue | 1280x900 | `output/playwright/topic5-guided-conversion-ui/13-review-1280x900.png` |
| Task Mapping | 1280x900 | `output/playwright/topic5-guided-conversion-ui/14-task-mapping-1280x900.png` |
| Task Mapping | 1024x768 | `output/playwright/topic5-guided-conversion-ui/15-task-mapping-1024x768.png` |
| Conversion Step 1 | 1024x768 | `output/playwright/topic5-guided-conversion-ui/16-conversion-step1-1024x768.png` |
| SchemaPacks | 1024x768 | `output/playwright/topic5-guided-conversion-ui/17-schemapacks-1024x768.png` |

## Visual And Accessibility Observations

- Inspected rendered 1440x1024, 1280x900, and 1024x768 screenshots for
  clipping, overlaps, unreadable contrast, hidden workflow actions, and table
  escape. No qualifying visual or accessibility defect was found.
- At 1024px, the Mapping table remains inside its focusable horizontal-scroll
  `DataTable` region; it does not escape the application shell.
- The 1024px workflow uses its narrow stacked layout and retains the sticky
  previous/next action footer above the viewport edge.
- The conversion flow was keyboard checked: Tab reached the enabled `下一步`
  control and Enter advanced to Step 2 after a valid imported UIR.
- The task tabs expose `tablist`, `tab`, and `tabpanel` semantics. The Review
  listbox accepted keyboard focus and Tab advanced to the enabled `采纳`
  control; `暂缓（当前 API 不支持）` stayed disabled and was not invoked.
- Status, alert, and empty states communicate text in addition to color. The
  user-facing UI was Chinese-first while retaining technical nouns such as
  UIR, SchemaPack, JSON, LLM, and Package.

No visual fixes were made. A non-visual follow-up remains: the global header
continued to display `后端状态：未连接` while proxied API requests were
successful. This is a runtime-status behavior mismatch, not a rendered
layout/accessibility defect, and was outside this visual-QA-only change scope.

## Self Reviews

### Specification Coverage

PASS. Covered every required named view at 1440x1024, completed the actual
Sample/validate/import/next/run flow, captured execution and task tabs from the
real generated task, checked Review keyboard traversal without mutating its
decision, and recorded all three requested desktop viewport sizes. Frontend
tests/build are passing; the repository gate timeout is explicitly not treated
as a pass.

### Code Quality

PASS. No application source was changed because screenshot inspection found no
qualifying visual or accessibility defect. The only committed deliverables are
this verification record and its browser screenshot evidence. Generated local
runtime state (`frontend/node_modules`, `frontend/dist`, Python caches,
database/storage, logs, and Playwright session metadata) remains uncommitted.

## Changed Files And API Contract

- Added this report.
- Added the 17 screenshot artifacts listed above.
- No frontend source was changed.
- No API request or response contract was changed.
