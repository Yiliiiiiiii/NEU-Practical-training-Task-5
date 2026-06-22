# Phase 8 Document Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 8 React frontend as a document-editor style workbench for the real SchemaPack Agent backend workflow.

**Architecture:** Add a new `frontend/` Vite React TypeScript app that talks to the existing FastAPI API through a focused client layer. Keep the UI as a single-page workbench with route-like state, shared shell components, real demo JSON fixtures, and no mock-only final path.

**Tech Stack:** React, TypeScript, Vite, Vitest, Testing Library, lucide-react, plain CSS with OKLCH tokens, FastAPI CORS middleware.

---

## File Map

- Create `frontend/package.json`: scripts and dependencies.
- Create `frontend/index.html`, `frontend/tsconfig*.json`, `frontend/vite.config.ts`: Vite app configuration and test setup.
- Create `frontend/src/api/client.ts`: typed fetch wrapper and API methods.
- Create `frontend/src/api/types.ts`: frontend API response/request types.
- Create `frontend/src/demo/*.json`: copied demo UIR, schema, and template files from `examples/demo`.
- Create `frontend/src/components/*.tsx`: shared shell, stage rail, status chips, JSON editor/viewer, empty states, tabs, toasts.
- Create `frontend/src/pages/*.tsx`: tasks, import/setup, mapping review, task detail, package/download views.
- Create `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/styles.css`: app state, entrypoint, design system.
- Create `frontend/src/__tests__/*.test.ts(x)`: API client helpers and key workflow state tests.
- Modify `backend/app/config.py`: add CORS origins setting.
- Modify `backend/app/main.py`: install CORS middleware.
- Add/modify backend tests for CORS behavior.
- Modify `README.md`: document Phase 8 status and frontend commands.

---

## Task 1: Backend CORS For Local Frontend

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_bootstrap.py`

- [ ] **Step 1: Write failing CORS test**

Add a test that sends an `OPTIONS` preflight from Vite's default origin:

```python
def test_cors_allows_local_frontend_preflight():
    from fastapi.testclient import TestClient
    from app.main import create_app

    client = TestClient(create_app(init_database=False))
    response = client.options(
        "/api/v1/tasks",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_bootstrap.py::test_cors_allows_local_frontend_preflight -q
```

Expected: FAIL because CORS middleware is not installed.

- [ ] **Step 3: Implement minimal CORS support**

Add `cors_origins` to settings and install `CORSMiddleware` in `create_app`.

Default origins:

```python
cors_origins: list[str] = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
```

- [ ] **Step 4: Verify backend target and full backend suite**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest tests/test_bootstrap.py::test_cors_allows_local_frontend_preflight -q
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/config.py backend/app/main.py backend/tests/test_bootstrap.py
git commit -m "feat: allow local frontend API access"
```

---

## Task 2: Scaffold Vite React App

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`

- [ ] **Step 1: Add frontend package files**

Create a Vite React TypeScript project with these scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "test": "vitest run"
  }
}
```

Use dependencies:

```json
"@vitejs/plugin-react", "vite", "typescript", "react", "react-dom",
"lucide-react", "vitest", "jsdom", "@testing-library/react",
"@testing-library/jest-dom", "eslint", "typescript-eslint",
"eslint-plugin-react-hooks", "eslint-plugin-react-refresh"
```

- [ ] **Step 2: Install dependencies**

Run:

```powershell
cd frontend
npm install
```

Expected: `node_modules/` and `package-lock.json` created.

- [ ] **Step 3: Add first smoke test**

Create a minimal render test:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("App", () => {
  it("renders the workbench shell", () => {
    render(<App />);
    expect(screen.getByText("SchemaPack Agent")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Verify frontend baseline**

Run:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add frontend
git commit -m "feat: scaffold phase 8 frontend"
```

---

## Task 3: API Client And Demo Fixtures

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/demo/example_uir_general_doc.json`
- Create: `frontend/src/demo/example_uir_policy_doc.json`
- Create: `frontend/src/demo/target_schema_general.json`
- Create: `frontend/src/demo/target_schema_policy.json`
- Create: `frontend/src/demo/mapping_template_general.json`
- Create: `frontend/src/demo/mapping_template_policy.json`
- Test: `frontend/src/__tests__/apiClient.test.ts`

- [ ] **Step 1: Write failing API helper tests**

Test URL joining and error extraction:

```ts
import { describe, expect, it } from "vitest";
import { buildApiUrl, extractApiError } from "../api/client";

describe("api client helpers", () => {
  it("joins base URL and path without duplicate slashes", () => {
    expect(buildApiUrl("http://x/api/v1/", "/tasks")).toBe("http://x/api/v1/tasks");
  });

  it("extracts FastAPI detail errors", async () => {
    const response = new Response(JSON.stringify({ detail: "task not found" }), {
      status: 404,
      headers: { "content-type": "application/json" },
    });
    await expect(extractApiError(response, "Load task")).resolves.toContain("task not found");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- apiClient
```

Expected: FAIL because helpers are missing.

- [ ] **Step 3: Implement typed client**

Implement methods for all endpoints listed in the design spec. The client must include:

```ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
export function buildApiUrl(base: string, path: string): string;
export async function apiRequest<T>(path: string, options?: RequestInit, label?: string): Promise<T>;
export async function downloadPackage(taskId: string): Promise<{ blob: Blob; sha256: string | null }>;
```

- [ ] **Step 4: Copy demo fixtures**

Copy exact JSON fixture contents from `examples/demo` into `frontend/src/demo`.

- [ ] **Step 5: Verify**

Run:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/api frontend/src/demo frontend/src/__tests__
git commit -m "feat: add frontend API client and demo fixtures"
```

---

## Task 4: App Shell And Design System

**Files:**
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/StageRail.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/ToastRegion.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/__tests__/shell.test.tsx`

- [ ] **Step 1: Write failing shell test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("workbench shell", () => {
  it("shows document workbench navigation", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /Import/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tasks/i })).toBeInTheDocument();
    expect(screen.getByText(/UIR -> Schema -> Template/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- shell
```

Expected: FAIL until components exist.

- [ ] **Step 3: Implement shell**

Create an app shell with:

- Header with product name, API base URL, current task ID, and refresh action.
- Left workflow rail with Import, Tasks, Mapping, Detail, Package.
- Main document pane.
- Toast/status region.

- [ ] **Step 4: Implement CSS tokens**

Use tokens from `DESIGN.md`, app-shell layout, responsive rail collapse, focus rings, button states, tables, code panels, tabs, and reduced-motion rules.

- [ ] **Step 5: Verify**

Run:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src
git commit -m "feat: add document workbench shell"
```

---

## Task 5: Import And Setup Workflow

**Files:**
- Create: `frontend/src/components/JsonWorkbench.tsx`
- Create: `frontend/src/pages/ImportPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/importPage.test.tsx`

- [ ] **Step 1: Write failing import page test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ImportPage } from "../pages/ImportPage";

describe("ImportPage", () => {
  it("offers demo UIR, schema, and template import panels", () => {
    render(<ImportPage />);
    expect(screen.getByText("UIR Document")).toBeInTheDocument();
    expect(screen.getByText("Target Schema")).toBeInTheDocument();
    expect(screen.getByText("Mapping Template")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Load general demo/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- importPage
```

Expected: FAIL until page exists.

- [ ] **Step 3: Implement import page**

The page must:

- Load general or policy demo fixture sets.
- Accept pasted JSON.
- Accept `.json` files.
- Validate parse errors locally.
- Call `POST /documents/import`, `POST /schemas`, `POST /templates`.
- Select imported IDs.
- Create task with `POST /tasks`.

- [ ] **Step 4: Verify**

Run:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src
git commit -m "feat: add import and setup workflow"
```

---

## Task 6: Tasks And Mapping Review

**Files:**
- Create: `frontend/src/pages/TasksPage.tsx`
- Create: `frontend/src/pages/MappingPage.tsx`
- Create: `frontend/src/components/MappingTable.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/mappingTable.test.tsx`

- [ ] **Step 1: Write failing mapping table test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MappingTable } from "../components/MappingTable";

describe("MappingTable", () => {
  it("marks review-required mappings", () => {
    render(<MappingTable mappings={[{
      mapping_id: "m1",
      task_id: "t1",
      candidate_id: "c1",
      source_name: "Title",
      source_path: "metadata.title",
      target_field_id: "title",
      target_field_name: "title",
      method: "alias_match",
      confidence: 0.72,
      status: "pending_review",
      need_review: true,
      evidence: ["alias"]
    }]} targetFields={["title"]} onReview={() => undefined} />);
    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- mappingTable
```

Expected: FAIL until component exists.

- [ ] **Step 3: Implement tasks page**

Show task table from `GET /tasks`, with status chips, IDs, and open action.

- [ ] **Step 4: Implement mapping page**

Actions:

- Generate candidates.
- Run mapping.
- Load candidates and mappings.
- Submit review decisions with `POST /mappings/review`.
- Support target field selection from the selected schema.

- [ ] **Step 5: Verify**

Run:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src
git commit -m "feat: add tasks and mapping review UI"
```

---

## Task 7: Task Detail, Reports, And Package Download

**Files:**
- Create: `frontend/src/pages/TaskDetailPage.tsx`
- Create: `frontend/src/pages/PackagePage.tsx`
- Create: `frontend/src/components/ReportTabs.tsx`
- Create: `frontend/src/components/CodePanel.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/reports.test.tsx`

- [ ] **Step 1: Write failing report tabs test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportTabs } from "../components/ReportTabs";

describe("ReportTabs", () => {
  it("renders mapping, validation, consistency, and trace tabs", () => {
    render(<ReportTabs reports={{ mapping: {}, validation: {}, consistency: {}, trace: {} }} />);
    expect(screen.getByRole("button", { name: /Mapping/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Validation/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Consistency/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Trace/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test -- reports
```

Expected: FAIL until report components exist.

- [ ] **Step 3: Implement task detail**

Task detail must:

- Load `GET /tasks/{task_id}`.
- Run `POST /convert`.
- Load canonical with `GET /canonical`.
- Load mapping, validation, consistency, and trace reports.
- Display JSON in readable code panels.

- [ ] **Step 4: Implement package page**

Package page must:

- Call `POST /package`.
- Show package ID, status, ZIP path, and SHA.
- Call `GET /package/download`.
- Save blob as `standard_package.zip`.
- Surface download response `X-SHA256`.

- [ ] **Step 5: Verify**

Run:

```powershell
cd frontend
npm run test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src
git commit -m "feat: add task reports and package download UI"
```

---

## Task 8: End-to-End Manual Verification And Docs

**Files:**
- Modify: `README.md`
- Optional modify: `DESIGN.md` if visual QA finds a design-system correction.

- [ ] **Step 1: Start backend**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Expected: backend serves `http://127.0.0.1:8000/health`.

- [ ] **Step 2: Start frontend**

Run:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

Expected: Vite serves `http://127.0.0.1:5173`.

- [ ] **Step 3: Complete general demo workflow in browser**

Workflow:

1. Load general demo set.
2. Import UIR, Schema, Template.
3. Create task.
4. Generate candidates.
5. Run mapping.
6. Review if needed.
7. Convert.
8. Load reports.
9. Package.
10. Download ZIP.

Expected: ZIP downloads, reports display, no layout overlap at desktop width.

- [ ] **Step 4: Check responsive layout**

Use browser viewport widths around 390px and 1280px. Expected: rail collapses, text does not overflow controls, core actions remain reachable.

- [ ] **Step 5: Update README**

Add:

```powershell
cd frontend
npm install
npm run dev
npm run test
npm run lint
npm run build
```

Also update current implementation status to Phase 8.

- [ ] **Step 6: Final gates**

Run:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
cd ..\frontend
npm run test
npm run lint
npm run build
cd ..
git diff --check
git status --short
```

Expected: all commands pass; `git diff --check` has no errors except possible CRLF warnings.

- [ ] **Step 7: Commit**

```powershell
git add README.md DESIGN.md frontend
git commit -m "docs: update phase 8 frontend instructions"
```

---

## External Design References Used

- Notion sidebar: nested document navigation and focused workspace structure.
- GitBook UI: sidebar/content editor split and documentation-oriented reading surfaces.
- Linear UI redesign: reduced visual noise, alignment, hierarchy, and navigation density.
- Airtable Interface Designer: repeatable review workflows and action buttons on data surfaces.

These references guide product patterns only. The implementation must remain a SchemaPack-specific workbench, not a clone.

## Completion Gate

Phase 8 is complete only when:

- The frontend runs with `npm run dev`.
- The frontend tests, lint, and build pass.
- Backend tests and Ruff still pass.
- The general demo can be completed through the UI against the real backend.
- Reports and package download work through UI controls.
- README reflects Phase 8.
- No Phase 9 or Phase 10 work is started.
