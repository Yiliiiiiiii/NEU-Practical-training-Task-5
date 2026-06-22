# Phase 8 Document Workbench Design

## Purpose

Phase 8 adds the minimum usable frontend for SchemaPack Agent. It must let a reviewer run and inspect the core pipeline without Swagger:

```text
UIR import -> Schema/Template setup -> Task creation -> Candidates -> Mapping -> Review -> Convert -> Reports -> Package -> Download
```

The UI should use the document-editor style chosen by the user: quiet, readable, structured, and strong at JSON/Markdown/report inspection.

## Scope

Build a new `frontend/` application with React and TypeScript.

Required screens:

1. `Tasks`: list tasks and open task detail.
2. `Import`: import UIR, Target Schema, and Mapping Template from file, pasted JSON, or bundled demo sample.
3. `Mapping`: generate candidates, run mapping, view mappings, and submit review decisions.
4. `Task Detail`: view task status, run conversion, inspect canonical model, mapping report, validation report, consistency report, and trace.
5. `Package`: generate package and download `standard_package.zip`.

The interface may implement these as route-like views inside one SPA rather than using a full router library.

## Non-goals

- No authentication.
- No Phase 10 external verifier UI.
- No real LLM fallback UI beyond showing the existing `enable_llm_fallback` toggle as disabled or off by default.
- No complex visualization library.
- No marketing landing page.
- No mock-only final workflow.

## Backend Contract

The frontend calls the existing FastAPI API under `/api/v1`.

Required endpoints:

- `POST /documents/import`
- `GET /documents`
- `POST /schemas`
- `GET /schemas`
- `GET /schemas/{schema_id}`
- `POST /templates`
- `GET /templates`
- `GET /templates/{template_id}`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `POST /tasks/{task_id}/generate-candidates`
- `GET /tasks/{task_id}/candidates`
- `POST /tasks/{task_id}/map`
- `GET /tasks/{task_id}/mappings`
- `POST /tasks/{task_id}/mappings/review`
- `GET /tasks/{task_id}/reports/mapping`
- `POST /tasks/{task_id}/convert`
- `GET /tasks/{task_id}/canonical`
- `POST /tasks/{task_id}/package`
- `GET /tasks/{task_id}/reports/validation`
- `GET /tasks/{task_id}/reports/consistency`
- `GET /tasks/{task_id}/trace`
- `GET /tasks/{task_id}/package/download`

The frontend should expose an API base URL setting through `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000/api/v1`.

## UX Flow

### First-run Demo

The UI should make the demo path fast:

1. Load bundled example JSON files from `frontend/src/demo`.
2. Import general or policy UIR.
3. Import matching schema and template.
4. Create a task from the selected three IDs.
5. Generate candidates.
6. Run mapping.
7. Review rows that need review.
8. Convert.
9. Package.
10. Download ZIP.

### Error Handling

All API failures should show:

- HTTP status when available.
- Backend `detail` or error body.
- The action that failed.
- A retry affordance near the failed action.

No failure should leave the user guessing whether the backend call happened.

### Loading States

Use local loading states per action. Avoid global blocking spinners. Buttons should show action-specific loading text, and tables should keep their last successful data visible.

## Visual Design

The workbench uses a light document surface, compact controls, and readable code/report panels.

Primary surfaces:

- App background: cool near-white.
- Panels: white or slightly tinted neutral.
- Borders: subtle neutral lines.
- Accent: calm blue for primary actions and selection.
- Semantic status: green, amber, red.

Use icons from `lucide-react` for actions such as import, refresh, run, confirm, package, download, file, report, and warning.

## Accessibility

- All controls must be reachable by keyboard.
- Focus rings must be visible.
- Buttons must not rely on icon-only meaning without labels or titles.
- Reduced motion must be respected.
- Text must not overflow buttons, navigation items, cards, or tables at desktop or mobile widths.

## Testing And Verification

Frontend verification:

- `npm run build`
- `npm run lint`
- At least a focused test or smoke script if the chosen tooling supports it.

Backend regression:

- Run backend `pytest -q` after adding any backend CORS support.
- Run backend `ruff check .`.

Manual/browser verification:

- Start backend.
- Start frontend.
- Complete the general demo workflow through the UI.
- Confirm reports load.
- Confirm ZIP download returns a file and the UI displays the ZIP SHA header when available.

## Acceptance Criteria

- The app starts from `frontend/` with `npm run dev`.
- The app builds with `npm run build`.
- It uses real backend API calls.
- It supports the demo workflow end to end.
- It has polished document-editor visual design.
- It is responsive enough for desktop and mobile review.
- README documents the frontend commands and Phase 8 status.
