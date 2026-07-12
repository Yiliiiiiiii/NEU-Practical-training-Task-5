# Topic 5 Guided Conversion Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Chinese-first, production-quality Topic 5 Guided Conversion Studio that preserves existing frontend API workflows and accurately exposes available conversion, review, result, lineage, and evidence capabilities.

**Architecture:** Replace the monolithic `App.tsx` with a small browser-History router, a reusable application shell, and route-level pages. Each page owns its own request lifecycle and transient state; shared modules hold API access, route helpers, status/formatting utilities, and common presentation. Conversion form recovery uses `sessionStorage` only and is explicitly not represented as a server draft.

**Tech Stack:** React 18, TypeScript, Vite, Lucide React, Vitest, Testing Library, CSS.

---

## File Structure

- Create: `frontend/src/app/router.ts` - browser History route parsing, navigation, and route hook.
- Create: `frontend/src/app/format.ts` - Chinese-first status, date, ID, error, and capability formatting.
- Create: `frontend/src/layouts/AppShell.tsx` - sidebar, global top bar, responsive shell, and navigation.
- Create: `frontend/src/layouts/WorkflowLayout.tsx` - workflow stepper, sticky context summary, and action footer.
- Create: `frontend/src/pages/overview/OverviewPage.tsx` - concise dashboard with recent tasks and service/evidence state.
- Create: `frontend/src/pages/conversion/ConversionPage.tsx` - four-step workflow orchestration and local session recovery.
- Create: `frontend/src/pages/conversion/uirValidation.ts` - JSON and minimal normalized UIR contract validation.
- Create: `frontend/src/pages/conversion/ConversionInputStep.tsx` - Paste UIR, External UIR, and Sample modes.
- Create: `frontend/src/pages/conversion/SchemaPackStep.tsx` - schema/template pair selection and detail view.
- Create: `frontend/src/pages/conversion/ConfigureStep.tsx` - typed configuration controls and summary.
- Create: `frontend/src/pages/conversion/ReviewRunStep.tsx` - execution review and truthful run action.
- Create: `frontend/src/pages/execution/ExecutionPage.tsx` - synchronous execution state and stage outcome view.
- Create: `frontend/src/pages/tasks/TasksPage.tsx` - task table, client-side search/filter/sort/pagination.
- Create: `frontend/src/pages/task-detail/TaskDetailPage.tsx` - result header, lazy reports, and tab composition.
- Create: `frontend/src/pages/task-detail/MappingTab.tsx` - evidence split pane with mapping state labels.
- Create: `frontend/src/pages/task-detail/ValidationTab.tsx` - grouped issue list and raw report disclosure.
- Create: `frontend/src/pages/task-detail/ContentTab.tsx` - organization facts and selected chunk viewer.
- Create: `frontend/src/pages/task-detail/PackageTab.tsx` - manifest/verifier trust presentation and download guard.
- Create: `frontend/src/pages/task-detail/ExecutionTab.tsx` - options, audit events, report paths, and unavailable capabilities.
- Create: `frontend/src/pages/review/ReviewPage.tsx` - queue/evidence split pane using supported decisions.
- Create: `frontend/src/pages/schemapacks/SchemaPacksPage.tsx` - catalog list/detail and preserved Schema Draft Lab.
- Create: `frontend/src/pages/evidence/EvidencePage.tsx` - preserved Evaluation Center and explicit evidence limitations.
- Create: `frontend/src/pages/settings/SettingsPage.tsx` - local runtime context and available integration visibility.
- Create: `frontend/src/components/status/StatusBadge.tsx` - accessible status badge.
- Create: `frontend/src/components/feedback/PageState.tsx` - loading, empty, offline, partial, and error states.
- Create: `frontend/src/components/tables/DataTable.tsx` - scroll-safe table wrapper.
- Modify: `frontend/src/api.ts` - add typed `listTasks` only; retain all existing endpoint contracts.
- Modify: `frontend/src/types.ts` - add `TaskListItem` and `TaskListResponse` only.
- Modify: `frontend/src/components/ExternalUirPanel.tsx` - Chinese-first copy and collapsed compatibility file import.
- Modify: `frontend/src/components/ReviewWorkbenchPanel.tsx` - use only supported Chinese approve/reject actions or move logic into ReviewPage.
- Modify: `frontend/src/components/*EvidencePanel.tsx` - retain behavior while replacing garbled copy with Chinese-first labels.
- Modify: `frontend/src/App.tsx` - reduce to route dispatch and shell composition.
- Modify: `frontend/src/styles.css` - replace old all-in-one layout with responsive enterprise design tokens and route/page styles.
- Create: `frontend/src/app/router.test.ts`, `frontend/src/pages/conversion/uirValidation.test.ts`, `frontend/src/pages/conversion/ConversionPage.test.tsx`, `frontend/src/pages/tasks/TasksPage.test.tsx`, `frontend/src/pages/task-detail/TaskDetailPage.test.tsx`, `frontend/src/pages/review/ReviewPage.test.tsx`, `frontend/src/layouts/AppShell.test.tsx`.
- Modify: existing frontend component tests only where labels intentionally change to Chinese-first copy.

## Task 1: Establish Routing, Types, API, and Shared Formatters

**Status:**
- [x] Task complete

**Dependencies:** None
**Parallelizable:** No (route and shared contracts are prerequisites for page integration)

**Files:**
- Create: `frontend/src/app/router.ts`
- Create: `frontend/src/app/format.ts`
- Create: `frontend/src/app/router.test.ts`
- Create: `frontend/src/components/status/StatusBadge.tsx`
- Create: `frontend/src/components/feedback/PageState.tsx`
- Create: `frontend/src/components/tables/DataTable.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Write failing route and formatting tests**

```ts
it("parses task and conversion execution routes", () => {
  expect(parseRoute("/tasks/task-42")).toEqual({ name: "taskDetail", taskId: "task-42" });
  expect(parseRoute("/conversions/executing/task-42")).toEqual({ name: "execution", taskId: "task-42" });
});

it("formats statuses in Chinese while preserving technical identifiers", () => {
  expect(formatStatus("review_required")).toBe("需要复核");
  expect(formatStatus("verified")).toBe("已验证");
});
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `npm test -- router.test.ts`

Expected: FAIL because `router.ts` and `format.ts` do not exist.

- [ ] **Step 3: Implement the narrow shared contract**

```ts
export type AppRoute =
  | { name: "overview" }
  | { name: "conversion" }
  | { name: "execution"; taskId: string }
  | { name: "tasks" }
  | { name: "taskDetail"; taskId: string }
  | { name: "review" }
  | { name: "schemaPacks" }
  | { name: "evidence" }
  | { name: "settings" };

export function parseRoute(pathname: string): AppRoute {
  const segments = pathname.split("/").filter(Boolean);
  if (segments[0] === "conversions" && segments[1] === "new") return { name: "conversion" };
  if (segments[0] === "conversions" && segments[1] === "executing" && segments[2]) {
    return { name: "execution", taskId: decodeURIComponent(segments[2]) };
  }
  if (segments[0] === "tasks" && segments[1]) return { name: "taskDetail", taskId: decodeURIComponent(segments[1]) };
  if (segments[0] === "tasks") return { name: "tasks" };
  if (segments[0] === "review") return { name: "review" };
  if (segments[0] === "schemapacks") return { name: "schemaPacks" };
  if (segments[0] === "evidence") return { name: "evidence" };
  if (segments[0] === "settings") return { name: "settings" };
  return { name: "overview" };
}

export function formatStatus(status: string): string {
  return ({
    completed: "已完成", verified: "已验证", review_required: "需要复核",
    failed: "失败", running: "进行中", pending: "待处理", blocked: "已阻断",
    unmapped: "未映射", unverified: "未验证"
  } as Record<string, string>)[status.toLowerCase()] ?? status;
}
```

Add `TaskListItem`/`TaskListResponse` to `types.ts` matching the current
`GET /api/v1/tasks` response, and add:

```ts
listTasks: (page = 1, pageSize = 100) =>
  request<TaskListResponse>(`/api/v1/tasks?page=${page}&page_size=${pageSize}`),
```

Do not alter existing request payloads or APIs. Build semantic `StatusBadge`,
`PageState`, and `DataTable` wrappers with Chinese user copy, `role="status"`/
`role="alert"` as applicable, and table overflow containment.

- [ ] **Step 4: Run focused tests and TypeScript build**

Run: `npm test -- router.test.ts && npm run build`

Expected: PASS and production bundle completes.

- [ ] **Step 5: Commit the shared foundation**

```bash
git add frontend/src/app frontend/src/api.ts frontend/src/types.ts frontend/src/components/status frontend/src/components/feedback frontend/src/components/tables
git commit -m "feat: add guided conversion app foundation"
```

## Task 2: Build Shell and Route Dispatch

**Status:**
- [x] Task complete

**Dependencies:** Task 1
**Parallelizable:** No (all pages render within the shell)

**Files:**
- Create: `frontend/src/layouts/AppShell.tsx`
- Create: `frontend/src/layouts/AppShell.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write a failing shell navigation test**

```tsx
it("marks New Conversion active and collapses the sidebar", async () => {
  render(<AppShell route={{ name: "conversion" }}>{<div>内容</div>}</AppShell>);
  expect(screen.getByRole("link", { name: "新建转换" })).toHaveAttribute("aria-current", "page");
  await userEvent.click(screen.getByRole("button", { name: "收起导航" }));
  expect(screen.getByLabelText("主导航")).toHaveClass("is-collapsed");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- AppShell.test.tsx`

Expected: FAIL because the app shell does not exist.

- [ ] **Step 3: Implement navigation and route dispatch**

```tsx
const navigation = [
  ["overview", "/", "概览"],
  ["conversion", "/conversions/new", "新建转换"],
  ["tasks", "/tasks", "任务"],
  ["review", "/review", "复核"],
  ["schemaPacks", "/schemapacks", "SchemaPacks"],
  ["evidence", "/evidence", "证据"],
  ["settings", "/settings", "设置"]
] as const;
```

Use Lucide icons, accessible links, a button with an explicit Chinese name for
collapse/expand, a small `local` environment label, backend status text, and a
local-session identity. Keep task actions out of the global top bar. `App.tsx`
becomes a route switch that passes route-level elements into `AppShell`.

- [ ] **Step 4: Replace legacy global CSS with scoped enterprise shell styles**

Define neutral white/gray surfaces, restrained blue primary, green success,
amber review, red failure, 8px radii, visible focus outlines, and responsive
breakpoints at 1280px/1024px. Do not use gradients, glass effects, oversized
cards, or garbled/English-only user labels.

- [ ] **Step 5: Run shell and existing frontend tests**

Run: `npm test -- AppShell.test.tsx && npm test`

Expected: PASS; legacy tests may require only intentional text expectation
updates, not behavior removal.

- [ ] **Step 6: Commit the shell**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/layouts frontend/src/styles.css frontend/src/layouts/AppShell.test.tsx
git commit -m "feat: add guided conversion application shell"
```

## Task 3: Implement the Four-Step Conversion Workflow

**Status:**
- [x] Task complete

**Dependencies:** Task 2
**Parallelizable:** No (workflow state and execution flow are a single user journey)

**Files:**
- Create: `frontend/src/layouts/WorkflowLayout.tsx`
- Create: `frontend/src/pages/conversion/uirValidation.ts`
- Create: `frontend/src/pages/conversion/uirValidation.test.ts`
- Create: `frontend/src/pages/conversion/ConversionInputStep.tsx`
- Create: `frontend/src/pages/conversion/SchemaPackStep.tsx`
- Create: `frontend/src/pages/conversion/ConfigureStep.tsx`
- Create: `frontend/src/pages/conversion/ReviewRunStep.tsx`
- Create: `frontend/src/pages/conversion/ConversionPage.tsx`
- Create: `frontend/src/pages/conversion/ConversionPage.test.tsx`
- Modify: `frontend/src/components/ExternalUirPanel.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing validation and workflow progression tests**

```ts
it("rejects unparsable JSON and UIRs without doc_id or blocks", () => {
  expect(validateUirText("{").valid).toBe(false);
  expect(validateUirText('{"doc_id":"x"}').valid).toBe(false);
});
```

```tsx
it("blocks the next step until a valid UIR is imported", async () => {
  render(<ConversionPage />);
  expect(screen.getByRole("button", { name: "下一步" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "载入示例" }));
  await userEvent.click(screen.getByRole("button", { name: "验证 JSON" }));
  expect(screen.getByRole("button", { name: "导入 UIR" })).toBeEnabled();
});
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run: `npm test -- uirValidation.test.ts ConversionPage.test.tsx`

Expected: FAIL because conversion modules do not exist.

- [ ] **Step 3: Implement input validation and Step 1**

Implement a pure `validateUirText` that parses JSON and requires nonempty
`doc_id` and `blocks` array, displaying parse and contract errors next to the
field. `ConversionInputStep` must provide Chinese-first tabs `粘贴 UIR`、
`External UIR`、`示例`, JSON format/copy/clear/validate/import actions, a line-wrap
toggle, document facts, and source block preview.

Move the existing file input in `ExternalUirPanel` into:

```tsx
<details>
  <summary>兼容导入</summary>
  <input
    id="external-json-file"
    type="file"
    accept="application/json,.json"
    onChange={(event) => void onFileSelected(event.currentTarget.files?.[0] ?? null)}
  />
</details>
```

Keep the normal External UIR flow paste-first. Retain routing evidence and
explicit confirmation; replace any LLM wording with `LLM 建议（未自动采纳）`.

- [ ] **Step 4: Implement Steps 2-4 and local recovery**

SchemaPack entries are compatible schema/template pairs. Disable archived
entries; show Chinese lifecycle, versions, required fields, aliases, metadata,
and a raw configuration disclosure. The configuration step uses typed selects,
numbers, and checkboxes for current `ContentOrganizationOptions`; it does not
invent unsupported provider fields. Review runs `api.createTask` then
`api.executeTask`, then navigates to `/conversions/executing/:taskId`.

Persist only serializable form fields under `schemapack:conversion-draft` in
`sessionStorage`; label the action `保留本地草稿`, and state it is browser-local.
Do not claim server draft persistence.

- [ ] **Step 5: Implement workflow semantics and layout**

`WorkflowLayout` renders four `aria-current="step"` steps, a sticky Chinese
context summary, inline warnings, a single primary action, and a narrow desktop
stacked fallback. The sidebar/right panel cannot block primary actions at 1024px.

- [ ] **Step 6: Run workflow and regression tests**

Run: `npm test -- uirValidation.test.ts ConversionPage.test.tsx routeSelection.test.ts && npm run build`

Expected: PASS with a production build.

- [ ] **Step 7: Commit conversion flow**

```bash
git add frontend/src/layouts/WorkflowLayout.tsx frontend/src/pages/conversion frontend/src/components/ExternalUirPanel.tsx frontend/src/styles.css
git commit -m "feat: add guided topic5 conversion workflow"
```

## Task 4: Implement Honest Execution and Task Detail Results

**Status:**
- [x] Task complete

**Dependencies:** Task 3
**Parallelizable:** No (execution navigation and result contract share task state)

**Files:**
- Create: `frontend/src/pages/execution/ExecutionPage.tsx`
- Create: `frontend/src/pages/task-detail/TaskDetailPage.tsx`
- Create: `frontend/src/pages/task-detail/MappingTab.tsx`
- Create: `frontend/src/pages/task-detail/ValidationTab.tsx`
- Create: `frontend/src/pages/task-detail/ContentTab.tsx`
- Create: `frontend/src/pages/task-detail/PackageTab.tsx`
- Create: `frontend/src/pages/task-detail/ExecutionTab.tsx`
- Create: `frontend/src/pages/task-detail/TaskDetailPage.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing result-state tests**

```tsx
it("shows verified package download only after verifier passes", async () => {
  mockTaskReports({ verifier: { passed: true, errors: [], warnings: [] } });
  render(<TaskDetailPage taskId="task-1" />);
  expect(await screen.findByRole("link", { name: "下载已验证 Package" })).toBeVisible();
});

it("labels LLM evidence as a suggestion instead of an accepted mapping", async () => {
  mockTaskReports({ mapping: mappingWithLlmSuggestion });
  render(<TaskDetailPage taskId="task-1" />);
  expect(await screen.findByText("LLM 建议（未自动采纳）")).toBeVisible();
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `npm test -- TaskDetailPage.test.tsx`

Expected: FAIL because task detail page does not exist.

- [ ] **Step 3: Implement factual execution page**

Use the stable stages `输入`、`字段映射`、`转换`、`元数据`、`内容组织`、
`验证`、`一致性`、`打包`、`校验`. While awaiting synchronous execution, show
`服务正在同步执行，当前 API 未提供实时阶段事件。` After return, render only
factual terminal/review indicators and a link to task detail. Do not animate
fake stage progress or imply polling telemetry.

- [ ] **Step 4: Implement result header and tabs**

Load task header first, then fetch reports independently with a per-report
`PageState`. Implement accessible `role="tablist"`, `role="tab"`, and
`role="tabpanel"` for `概览`、`映射`、`验证`、`内容`、`Package`、`谱系`、`执行`.
The overview reports only operational facts and output readiness.

- [ ] **Step 5: Implement detailed report tabs**

`MappingTab` derives source name, path, target field, confidence, score margin,
evidence, alternatives, risk flags, and state from the existing flexible report
records. Clearly map supported status strings to `自动采纳`、`需要复核`、`已阻断`、
`未映射`、`LLM 建议（未自动采纳）`.

`ValidationTab` groups by severity/stage/path/code, displays suggested action,
and exposes raw JSON only in `<details>`. `ContentTab` uses the existing chunk
report, tags, summaries, entities where available, and a selected item view.
`PackageTab` prominently displays verifier/artifact state, manifest facts,
file/checksum table, and disables download when unverified. `ExecutionTab`
shows options, report paths, audit logs, fingerprint/hash values, plus disabled
`重放` and `重新验证` buttons with an explanatory tooltip because no API exists.
Retain the current `LineagePanel` in the Lineage tab.

- [ ] **Step 6: Run result tests and build**

Run: `npm test -- TaskDetailPage.test.tsx LineagePanel.test.tsx && npm run build`

Expected: PASS.

- [ ] **Step 7: Commit task result experience**

```bash
git add frontend/src/pages/execution frontend/src/pages/task-detail frontend/src/styles.css
git commit -m "feat: add conversion execution and task results"
```

## Task 5: Implement Tasks, Review, SchemaPacks, Evidence, Settings, and Overview

**Status:**
- [x] Task complete

**Dependencies:** Task 2
**Parallelizable:** Yes (can proceed alongside Task 3/4 after the shell interface is stable; integrate after Task 4)

**Files:**
- Create: `frontend/src/pages/overview/OverviewPage.tsx`
- Create: `frontend/src/pages/tasks/TasksPage.tsx`
- Create: `frontend/src/pages/tasks/TasksPage.test.tsx`
- Create: `frontend/src/pages/review/ReviewPage.tsx`
- Create: `frontend/src/pages/review/ReviewPage.test.tsx`
- Create: `frontend/src/pages/schemapacks/SchemaPacksPage.tsx`
- Create: `frontend/src/pages/evidence/EvidencePage.tsx`
- Create: `frontend/src/pages/settings/SettingsPage.tsx`
- Modify: `frontend/src/components/ReviewWorkbenchPanel.tsx`
- Modify: `frontend/src/components/SchemaDraftLabPanel.tsx`
- Modify: `frontend/src/components/EvaluationCenterPanel.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing task/review tests**

```tsx
it("filters tasks by text and opens a task detail route", async () => {
  mockListTasks([task("alpha"), task("beta")]);
  render(<TasksPage />);
  await userEvent.type(await screen.findByLabelText("搜索任务"), "beta");
  expect(screen.queryByText("alpha")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("link", { name: "打开 beta" }));
  expect(window.location.pathname).toBe("/tasks/beta");
});

it("provides supported review decisions and not a fake defer action", async () => {
  render(<ReviewPage />);
  expect(await screen.findByRole("button", { name: "采纳" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "暂缓（当前 API 不支持）" })).toBeDisabled();
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm test -- TasksPage.test.tsx ReviewPage.test.tsx`

Expected: FAIL because the pages do not exist.

- [ ] **Step 3: Implement Overview and Tasks**

Overview loads only task/review/evidence summaries, has one primary `新建转换`
action, recent task rows, pending review count, local service state, and latest
evidence gate. Tasks uses a table with requested columns where the API provides
data; unavailable counts render `—`, not invented values. Add Chinese search,
status/SchemaPack client filters, sort, pagination, refresh, empty/error states,
and valid `打开`/download actions. Render replay/reverify disabled with reasons.

- [ ] **Step 4: Implement Review Inbox**

Use existing review list, grouped list, impact preview, and approve/reject APIs.
Show a queue left and evidence/impact right. Preserve keyboard selection and
clear `LLM 建议（未自动采纳）` labels when `suggested_by` identifies an LLM. Expose
only `采纳` and `拒绝` as active controls; render the unavailable `暂缓` honestly.

- [ ] **Step 5: Implement SchemaPacks, Evidence, and Settings**

SchemaPacks uses catalog list-detail, schema fields, aliases, templates,
compatibility/status labels, raw configuration disclosure, and a second tab for
the retained Schema Draft Lab. It does not add activation automation.

Evidence embeds/adapts Evaluation Center and shows dataset, commit, reproduction
path, claim boundary, package-verification limitation, and any `not_run` status.
Settings is a compact read-only context page for API base/environment/session and
does not pretend those values can update unavailable backend configuration.

- [ ] **Step 6: Convert remaining legacy visible strings to Chinese-first text**

Correct garbled strings in `ReviewWorkbenchPanel`, `SchemaDraftLabPanel`,
`EvaluationCenterPanel`, `MappingEvidencePanel`, `ValidationIssuePanel`,
`ChunkEvidencePanel`, `PackageManifestPanel`, and `LineagePanel`. Preserve
technical nouns such as `Schema`, `SchemaPack`, `JSON`, `UIR`, `LLM`, `Chunk`,
`Package`, `SHA-256`, and endpoint-related identifiers in English.

- [ ] **Step 7: Run focused and regression tests**

Run: `npm test -- TasksPage.test.tsx ReviewPage.test.tsx EvaluationCenter.test.tsx && npm test`

Expected: PASS.

- [ ] **Step 8: Commit operational pages**

```bash
git add frontend/src/pages frontend/src/components/ReviewWorkbenchPanel.tsx frontend/src/components/SchemaDraftLabPanel.tsx frontend/src/components/EvaluationCenterPanel.tsx frontend/src/components/MappingEvidencePanel.tsx frontend/src/components/ValidationIssuePanel.tsx frontend/src/components/ChunkEvidencePanel.tsx frontend/src/components/PackageManifestPanel.tsx frontend/src/components/LineagePanel.tsx frontend/src/styles.css
git commit -m "feat: add guided conversion operations pages"
```

## Task 6: Integrate Pages, Remove Obsolete Workbench, and Add Regression Coverage

**Status:**
- [x] Task complete

**Dependencies:** Task 4, Task 5
**Parallelizable:** No (requires all route-level modules)

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/evaluationView.test.ts`
- Modify: `frontend/src/evidence.test.ts`
- Modify: `frontend/src/reviewBatchSafety.test.ts`
- Modify: `frontend/src/schemaDraftSamples.test.ts`
- Modify: `frontend/src/routeSelection.test.ts`
- Delete: obsolete inlined `App.tsx` workbench helper components only after imports/tests prove their route equivalents exist.

- [ ] **Step 1: Write a failing direct-route integration test**

```tsx
it("renders a task detail directly from its URL", () => {
  window.history.replaceState({}, "", "/tasks/task-direct");
  render(<App />);
  expect(screen.getByRole("heading", { name: "任务详情" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify failure or mismatch**

Run: `npm test -- AppShell.test.tsx`

Expected: FAIL until final route dispatch includes task detail.

- [ ] **Step 3: Complete the dispatch map and remove the old dense layout**

Every current capability must be reachable through a named route or task tab
before deleting code. Remove the original giant sidebar/report-grid markup and
its local state only after its behavior has been migrated. Keep no orphaned
imports or duplicate panel rendering.

- [ ] **Step 4: Add accessibility and language regression checks**

Assert labeled controls, tab roles, alert/status roles, focus-visible styling,
active navigation, and Chinese primary text on the main conversion/overview/task
paths. Permit only domain terms (`Schema`, `SchemaPack`, `JSON`, `UIR`, `LLM`,
`Chunk`, `Package`, hashes, IDs, endpoint paths) to remain English.

- [ ] **Step 5: Run all frontend verification**

Run: `npm test && npm run build`

Expected: all frontend tests pass and `vite build` completes.

- [ ] **Step 6: Commit the integrated frontend**

```bash
git add frontend/src
git commit -m "refactor: replace dense topic5 workbench"
```

## Task 7: Visual QA, Repository Verification, and Final Report

**Status:**
- [x] Task complete

**Dependencies:** Task 6
**Parallelizable:** No (requires final integrated build)

**Files:**
- Create: `docs/nbl/verification/2026-07-12-topic5-guided-conversion-ui.md`
- Create: `docs/nbl/verification/screenshots/` with PNGs for overview, conversion steps 1-4, execution, task overview, mapping, package, tasks, SchemaPacks, and evidence.
- Modify: only files necessary to correct defects found by rendered inspection.

- [ ] **Step 1: Start backend and frontend locally**

Run the documented backend command and:

```bash
cd frontend
npm run dev -- --port 5173
```

Expected: local frontend URL is available, with `VITE_API_BASE` set when needed.

- [ ] **Step 2: Capture requested views at each desktop width**

Use Playwright to visit all required routes at 1440x1024, 1280x900, and
1024x768. Capture screenshots for Overview; New Conversion steps 1-4; Execution;
Task Overview; Mapping; Package; Tasks; SchemaPacks; and Evidence.

- [ ] **Step 3: Inspect visual and accessibility outcomes**

Check screenshots for clipped controls, table overflow, hidden sticky action,
misaligned spacing, unreadable contrast, card nesting, and overlap. Use keyboard
tab traversal on the conversion flow, task tabs, and review queue. Correct only
issues found by the inspection, then repeat captures for affected views.

- [ ] **Step 4: Run final frontend and repository verification**

Run:

```bash
cd frontend
npm test
npm run build
```

Then run the project-required repository verification command from README or
the relevant Topic 5 verification document. Record its exact command and result;
do not claim a pass if unrelated existing worktree changes cause a failure.

- [ ] **Step 5: Write the verification report**

Record branch, final SHA, route/component map, changed and removed files, API
contract changes (expected: none), screenshot paths, commands/results,
accessibility checks, constraints caused by missing backend endpoints, and
remaining follow-up work. Cite that UI text is Chinese-first with preserved
technical terms.

- [ ] **Step 6: Commit verification evidence**

```bash
git add docs/nbl/verification frontend/src
git commit -m "docs: verify guided conversion studio"
```

---
**Execution Mode:** parallel
