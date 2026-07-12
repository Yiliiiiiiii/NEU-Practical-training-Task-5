# Topic 5 Guided Conversion Studio Design

## Purpose

Replace the dense, single-screen Topic 5 workbench with a desktop-oriented
Guided Conversion Studio. Operators move from an accepted normalized UIR to a
verified downstream package through a four-step flow, while all existing Topic
5 capabilities remain reachable in focused pages.

## Scope and Constraints

- Preserve the current React, TypeScript, Vite, Lucide, Vitest, and Testing
  Library stack.
- Preserve existing API request and response contracts. The frontend will not
  require backend endpoint changes.
- Stay within Topic 5: normalized UIR, existing External UIR conversion,
  schema/template selection, mapping, content organization, validation,
  artifacts, verification, lineage, review, and engineering evidence.
- Do not add raw-office-document input, OCR, embeddings, RAG, publication, or
  automatic LLM/schema activation controls.
- Keep External UIR JSON file selection only inside a collapsed compatibility
  import section. The primary External UIR path is JSON paste.

## API Capability Boundary

The current API supports catalog loading, UIR import, External UIR conversion
and import, task creation and synchronous execution, task/report/package reads,
package download, lineage, review approve/reject, schema drafts, knowledge
governance, audit logs, and evaluation center reads.

The current API does not expose task replay, package re-verification, task draft
persistence, stage progress events, or individual review defer. The UI will not
simulate these capabilities. Unsupported actions remain disabled with an
explanation; the existing supported review actions remain available.

## Route Map

| Route | Page | Primary responsibility |
| --- | --- | --- |
| `/` | Overview | Start conversion, recent tasks, review count, service/evidence state |
| `/conversions/new` | New Conversion | Four-step input, selection, configuration, and review flow |
| `/conversions/executing/:id` | Execution | Honest synchronous-submission state and terminal outcome |
| `/tasks` | Tasks | Searchable/filterable task table with valid actions |
| `/tasks/:id` | Task Detail | Result summary and focused report tabs |
| `/review` | Review Inbox | Queue and evidence/impact decision pane |
| `/schemapacks` | SchemaPacks | Schema/template list-detail and Schema Draft Lab |
| `/evidence` | Evidence | Evaluation scorecard, datasets, runs, and gate limits |
| `/settings` | Settings | Local session and integration visibility, no fabricated server controls |

The implementation uses browser History and a small local router utility rather
than a routing dependency. Direct URL loading and browser back/forward update
the application page state.

## Application Structure

```
frontend/src/
  app/                 application state, local routing, formatting utilities
  layouts/             AppShell and workflow/page framing
  pages/               overview, conversion, execution, tasks, task detail,
                       review, schemapacks, evidence, settings
  components/          retained evidence, lineage, external UIR, draft, and
                       focused shared UI modules
  api.ts               preserved API service with only missing list helpers added
  types.ts             preserved contracts with task-list type additions
  styles.css           calm enterprise visual system and responsive layout
```

There is no global data store. The shell owns navigation; each page owns its own
server loading, error state, and transient form state. The conversion workflow
persists safe unfinished form data in session storage so a browser refresh does
not silently discard it. This is local recovery, not a server-side task draft.

## Conversion Flow

`New Conversion` is a full-page four-step route with a horizontal stepper,
main working column, and sticky context summary.

1. **Input UIR**: segmented Paste UIR, External UIR, and Sample modes. Paste
   has a JSON editor with format, validation, copy, clear, parse/contract
   errors, document facts, and source block preview. External UIR embeds the
   existing conversion and deterministic routing flow, labels LLM output as a
   suggestion, and moves file loading into a compatibility disclosure.
2. **Select SchemaPack**: schema/template pairs are shown as selectable
   SchemaPacks. Cards/table rows show compatible status, versions, required
   count, aliases, metadata and content defaults. Selection remains explicit;
   External UIR routing is a recommendation with evidence, never an automatic
   irreversible choice.
3. **Configure Conversion**: typed mapping and content controls use existing
   `ContentOrganizationOptions`. Common options are visible; derived/legacy
   behavior is explained in a collapsed advanced section. The page shows a
   readable configuration summary and an optional raw request disclosure.
4. **Review and Run**: input, SchemaPack, configuration, warnings, and expected
   artifacts are summarized. `Run conversion` imports/creates a task where
   needed, then calls the current synchronous execute endpoint.

The summary reports input validity, document, selected SchemaPack, mapping mode,
chunk strategy, summary/provider choices, warnings, and readiness at every step.
Users cannot advance before validating/importing the input and selecting a
compatible SchemaPack.

## Execution and Results

The execution page shows the stable pipeline stages and distinguishes submission
from real stage telemetry. While the API call is outstanding it states that the
service is executing synchronously. On completion it marks only factual result
states based on task/report data and directs to task detail. It never creates a
fictional live stage stream.

Task Detail loads only the reports that exist and uses tabs:

- Overview: mapping/review/unmapped/validation/chunk/package readiness facts.
- Mapping: source, selected evidence, and target field split-pane with clear
  automatic/review/blocked/unmapped/LLM-suggestion badges.
- Validation: issues grouped by severity/stage/path/code and a raw disclosure.
- Content: document organization plus chunk list and selected chunk evidence.
- Package: verifier prominence, manifest file table, hashes, and verified-only
  download behavior.
- Lineage: existing graph and query capability plus table/list fallback.
- Execution: task options, report paths, audit records, fingerprints, and
  explicit absent-capability notices.

## Existing Workflow Migration

| Existing capability | New location |
| --- | --- |
| Normalized UIR import and sample | Conversion step 1 |
| External UIR adapter and routing | Conversion step 1 External UIR mode |
| Task creation/execution | Conversion review and execution pages |
| Mapping, validation, content, manifest | Task Detail tabs |
| Package download and downstream readiness | Task Detail Package tab |
| Lineage panel | Task Detail Lineage tab |
| Review workbench | Review Inbox |
| Schema Draft Lab | SchemaPacks secondary tab |
| Knowledge governance | Review/SchemePacks secondary panels |
| Evaluation Center | Evidence page |
| Audit logs | Task Detail Execution tab |

## Design and Accessibility

The visual system is a neutral near-white technical workspace with white working
surfaces, a restrained blue primary action, green success, amber review, and red
blocking errors. It uses a compact 8px radius, an 8px spacing scale, system
sans-serif text, and monospace only for IDs, paths, JSON, and hashes. Pages use
tables, split panes, tabs, grouped lists, disclosures, and compact badges rather
than dashboard-card grids.

Semantic controls, labels, `aria-current`, tab roles, keyboard-focus outlines,
disclosure semantics, status text, and `role=alert` error messages are required.
Desktop breakpoints at 1280px and 1024px collapse the sidebar, stack the workflow
summary below the work area, preserve the primary action, and allow wide tables
to scroll horizontally.

## Verification Plan

- Preserve and adapt existing component tests.
- Add focused tests for browser route selection, sidebar collapse, direct route
  loading, workflow progression gates, SchemaPack selection, advanced settings,
  conversion submission, task result states, package verification state, mapping
  status labeling, and accessible tabs/controls.
- Run `npm test` and `npm run build` from `frontend`.
- Run the repository verification script identified by project documentation.
- Launch the frontend with the backend, capture and inspect the requested views
  at 1440px, 1280px, and 1024px, and correct visual regressions.

## Acceptance Criteria

Completion requires a comprehensible four-step conversion flow, preserved
backend compatibility, access to all existing workflows, decomposed App code,
truthful execution state, readable evidence and validation, separated content
and package views, prominent package verification, clear LLM-suggestion labels,
desktop responsive layouts, accessibility basics, passing frontend tests/build,
repository verification, and actual screenshot-based visual QA.
