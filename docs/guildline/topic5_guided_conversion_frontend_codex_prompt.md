# Codex Prompt — SchemaPack Agent Frontend Redesign

## Goal

Redesign the existing frontend of:

```text
https://github.com/Yiliiiiiiii/NEU-Practical-training-Task-5
```

into a production-quality **Guided Conversion Studio** centered on a clear, step-by-step Topic 5 conversion workflow.

The redesign must preserve all working backend contracts and existing Topic 5 functionality while replacing the current dense, all-in-one workbench layout with a focused, understandable, enterprise-grade experience.

Do not return only a design proposal. Inspect the repository, create a dedicated branch, implement the redesign, run tests, visually verify the result, and provide a final implementation report.

---

# 1. Product Context

SchemaPack Agent is a Topic 5 data format standardization conversion system.

Its core input is:

```text
Normalized UIR
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
```

Its core output is:

```text
Field-aligned structured JSON
+ Markdown full text
+ Chunks with tags, summaries, entities, and source links
+ Document metadata
+ Manifest and checksums
+ Verified standard package
```

The frontend must help users complete this flow clearly:

```text
Input UIR
→ Select SchemaPack
→ Configure Conversion
→ Review
→ Execute
→ Inspect Results
→ Download Verified Package
```

---

# 2. Strict Topic 5 Boundary

The redesigned frontend must focus only on:

- normalized UIR input;
- External UIR input already supported by the project;
- target Schema and SchemaPack selection;
- metadata template;
- mapping rules;
- deterministic field transformation;
- content organization;
- chunk configuration;
- automatic field mapping;
- review-required mapping evidence;
- validation issues;
- document summary;
- tags and entity passthrough;
- artifact consistency;
- manifest and package verification;
- replay;
- verified downstream export;
- lineage and execution evidence.

Do not add UI for:

- raw PDF, Word, Excel, image, or scanned-document upload;
- OCR;
- document cleaning or semantic normalization;
- entity recognition or entity linking;
- quality scoring or quality grades;
- publication routing;
- RAG chat;
- vector databases;
- embeddings;
- training or fine-tuning;
- multi-agent orchestration;
- automatic LLM rule activation;
- automatic SchemaPack activation from LLM output.

LLM-generated content, when shown, must be clearly labeled as a suggestion and must never look automatically accepted.

---

# 3. Existing Frontend Constraints

Inspect the current frontend before editing.

Current stack is expected to include:

```text
React
TypeScript
Vite
Lucide React
Vitest
Testing Library
```

Preserve existing backend API contracts.

Do not rewrite the backend as part of this task.

Do not remove existing frontend capabilities merely because the new layout hides them initially.

Map every existing workflow into the new information architecture before deleting or replacing existing UI.

Create a feature branch:

```text
feat/topic5-guided-conversion-ui
```

---

# 4. Primary Design Direction

Use the following visual and interaction direction:

## Guided Conversion Studio

The main product experience should be a focused, step-based workflow rather than a large dashboard containing every feature simultaneously.

Target viewport:

```text
1440 × 1024 desktop web application
```

Primary users:

- data operations engineers;
- data standardization operators;
- mapping reviewers;
- project demonstrators;
- administrators performing conversion verification.

Primary user outcome:

> A user should always understand what input is being processed, which SchemaPack is active, what configuration will be used, what step comes next, and whether the final package is trustworthy.

---

# 5. Global Information Architecture

Use a compact application shell with:

```text
Overview
New Conversion
Tasks
Review
SchemaPacks
Evidence
Settings
```

However, the **New Conversion** flow is the hero workflow and receives the strongest product emphasis.

The sidebar should be compact and collapsible.

The top bar should show only essential global context:

- application name;
- environment;
- service health;
- backend version;
- active user or local session;
- optional theme control.

Do not overload the top bar with task-specific actions.

---

# 6. New Conversion Workflow

Build a four-step guided workflow.

```text
1. Input UIR
2. Select SchemaPack
3. Configure Conversion
4. Review and Run
```

Use a horizontal stepper at the top.

The layout should use:

```text
Main working area on the left
Sticky context summary on the right
```

The sticky right panel must update as the user progresses and summarize:

- document;
- UIR validity;
- SchemaPack;
- mapping mode;
- chunk strategy;
- provider;
- warnings;
- readiness to run.

Do not use a wizard modal.

Use a full-page workflow.

---

## Step 1 — Input UIR

Support the project’s existing input methods:

- paste normalized UIR JSON;
- load a built-in sample;
- use existing External UIR flow;
- import an already supported UIR document;
- validate JSON structure;
- preview normalized document structure.

Required UI sections:

### Input mode selector

Use lightweight tabs or segmented controls:

```text
Paste UIR
External UIR
Sample
```

Do not include raw file upload.

### UIR editor

Requirements:

- large readable code editor or enhanced textarea;
- syntax-like styling;
- line wrapping control;
- formatting action;
- validation action;
- copy and clear actions;
- visible parse errors;
- field-level contract errors where available;
- monospace typography;
- no oversized decorative container.

### Document preview

After successful validation, show:

```text
doc_id
UIR version
block count
asset count
entity count
metadata keys
source information
```

Show a compact source-block preview.

Do not show full raw JSON and full preview at the same time unless the screen has enough room.

### Step completion

The user cannot continue until:

- JSON parses;
- required UIR contract fields exist;
- the document is accepted by the current frontend validation flow.

---

## Step 2 — Select SchemaPack

The user should choose a complete SchemaPack rather than independently selecting unrelated configuration pieces whenever the backend allows it.

Show SchemaPack options in a structured list or table.

Each option should display:

```text
SchemaPack name
Schema ID
Schema version
Mapping Rules version
Metadata Template version
Content Organization version
Lifecycle status
Required field count
Compatibility status
```

Required states:

```text
Active
Draft
Deprecated
Archived
Incompatible
```

Only selectable states should be enabled.

Selecting a SchemaPack should open a detail panel containing:

- short purpose;
- target fields;
- required fields;
- mapping aliases;
- metadata fields;
- default chunk strategy;
- content tag configuration;
- compatibility warnings.

Do not expose raw configuration JSON by default.

Provide an expandable “View configuration” section.

### Selection guidance

Show:

- recommended SchemaPack when routing evidence exists;
- why it was recommended;
- whether it came from deterministic routing or external suggestion;
- clear warning when no reliable recommendation exists.

A recommendation must not be styled as an automatic irreversible selection.

---

## Step 3 — Configure Conversion

Show common settings first.

Advanced settings must be collapsed by default.

### Basic settings

Include only high-value controls:

```text
Mapping mode
Chunk strategy
Target tokens
Minimum tokens
Maximum tokens
Overlap tokens
Protect tables
Protect lists
Protect code blocks
Document summary
Chunk summary
Keyword extraction
Chunk provider
Fallback behavior
```

Use typed controls:

- select;
- numeric input;
- switch;
- checkbox;
- radio group.

Do not use free-form JSON for common settings.

### Advanced settings

Place under a disclosure component:

```text
Advanced settings
```

Include only controls already supported by the backend contract.

Do not invent unsupported options.

Show deprecation warnings for legacy fields.

When values conflict, explain the conflict inline.

### Configuration preview

Display a compact, human-readable configuration summary.

Do not force users to interpret raw request JSON.

Allow optional raw request preview in a secondary panel.

---

## Step 4 — Review and Run

This step must answer:

```text
What will be processed?
Which SchemaPack will be used?
Which settings are active?
What risks or warnings exist?
What will be generated?
```

Show:

### Input summary

- document ID;
- block count;
- metadata count;
- entity count.

### SchemaPack summary

- SchemaPack;
- target Schema;
- mapping rules;
- metadata template;
- content organization version.

### Execution summary

- mapping mode;
- review threshold;
- chunk provider;
- summary mode;
- package features.

### Warnings

Examples:

- deprecated option;
- review likely;
- external provider fallback enabled;
- missing optional metadata;
- incompatible configuration;
- strict mode enabled.

### Output preview

List expected artifacts:

```text
content.json
content.md
chunks.jsonl
metadata.json
mapping_report.json
validation_report.json
artifact_consistency_report.json
manifest.json
verified package ZIP
```

### Primary action

Use one clear primary action:

```text
Run conversion
```

Secondary actions:

```text
Back
Save draft
```

Do not place many equally weighted buttons.

---

# 7. Execution Experience

After the user starts a conversion, transition to a dedicated execution view.

Do not keep the wizard form visible beside a running task.

Show a clear stage progress component:

```text
Input
→ Mapping
→ Transform
→ Metadata
→ Content Organization
→ Validation
→ Artifact Consistency
→ Package
→ Verification
```

Each stage should support:

```text
pending
running
completed
review required
failed
skipped
```

Show:

- current stage;
- elapsed time;
- task ID;
- conversion fingerprint;
- SchemaPack version;
- retryability;
- error code when failed.

Do not simulate real-time progress if the backend does not expose it.

When only terminal status is available, show honest polling-based state.

---

# 8. Result Experience

After execution, show a task result page.

The result page should not display every report at once.

Use a clear summary followed by tabs.

## Result header

Show:

```text
Task ID
Document
Status
SchemaPack
Duration
Created time
Replay
Reverify package
Download package
```

Use one primary action based on state:

```text
Download verified package
or
Review issues
or
Inspect failure
```

## Stage summary

Show the completed conversion stages and any failed/review-required stage.

## Tabs

Use:

```text
Overview
Mapping
Validation
Content
Package
Lineage
Execution
```

---

## Overview tab

Show only the essential result:

- automatic mappings;
- review-required mappings;
- required unmapped fields;
- validation errors;
- chunk count;
- document summary;
- package verification result;
- major warnings;
- output readiness.

Avoid generic vanity metrics.

---

## Mapping tab

Use a professional split-pane workbench.

Recommended layout:

```text
Source candidates
│
Selected mapping evidence
│
Target Schema fields
```

Required information:

- source field;
- value sample;
- inferred type;
- source path;
- source block;
- evidence type;
- target field;
- target constraints;
- calibrated confidence;
- score margin;
- feature score breakdown;
- negative-pair checks;
- risk flags;
- alternatives;
- source backlinks;
- mapping status.

Clearly distinguish:

```text
Automatically accepted
Review required
Blocked
Unmapped
LLM suggestion
```

Review actions:

```text
Accept
Reject
Defer
```

Only show actions supported by current APIs.

Do not implement fake review actions.

---

## Validation tab

Group issues by:

```text
severity
stage
field path
error code
```

Each issue should display:

- message;
- exact path;
- stage;
- error code;
- related source blocks;
- suggested operator action where known.

Do not show only raw JSON.

Provide raw report as an expandable secondary view.

---

## Content tab

Allow users to inspect:

```text
Document summary
Markdown preview
Structured JSON
Chunks
Content tags
Management tags
Quality tags
Entity passthrough
Source backlinks
```

Use sub-tabs or split views.

Do not show all content formats at once.

Chunk list rows should show:

```text
chunk ID
title path
source block IDs
summary
keywords
tags
entities
quality flags
```

---

## Package tab

Show package trust clearly.

Include:

```text
Verifier status
Artifact consistency status
Manifest version
Package version
File count
Total bytes
Checksums
Feature declarations
Semantic fingerprint
ZIP hash
```

Display package files in a table:

```text
File
Role
Required
Media type
Bytes
Checksum
Status
```

Primary action:

```text
Download verified package
```

Disable or warn when verification failed.

Show downstream exports only for verified packages.

---

## Lineage tab

Preserve existing lineage capability.

Show:

- field lineage;
- block lineage;
- chunk lineage;
- artifact lineage;
- broken-edge status.

Do not make the graph the only representation.

Provide a readable table/list alternative.

---

## Execution tab

Show:

```text
stage durations
provider calls
fallback events
error details
conversion fingerprint
semantic hashes
replay comparison
execution snapshot
```

Operational data should remain separate from business document content.

---

# 9. Tasks Page

Build a dedicated task table.

Columns:

```text
Task
Document
SchemaPack
Status
Mapped
Review
Errors
Chunks
Created
Duration
Actions
```

Features:

- search;
- status filter;
- SchemaPack filter;
- date filter;
- sorting;
- pagination;
- empty state;
- error state;
- refresh.

Actions:

```text
Open
Replay
Reverify
Download
```

Only enable actions valid for the task state.

Use table rows, not one card per task.

---

# 10. Review Page

Build a Review Inbox.

Group review items by:

```text
Low confidence
Mapping conflict
Blocked pair
Required field
Validation issue
Provider fallback
```

Recommended layout:

```text
Review queue on the left
Evidence and decision panel on the right
```

Show:

- source;
- target;
- confidence;
- alternatives;
- evidence;
- risk;
- source blocks;
- task context;
- impact preview.

Actions:

```text
Accept
Reject
Defer
```

Make review actions visually distinct from automatic mapping.

LLM suggestions must use a clear “Suggestion” label.

---

# 11. SchemaPacks Page

Use a list-and-detail layout.

List columns:

```text
SchemaPack
Schema
Version
Status
Fields
Required fields
Compatibility
Updated
```

Detail sections:

```text
Overview
Target Schema
Mapping Rules
Metadata Template
Content Organization
Examples
Versions
Compatibility
```

Raw configuration should be secondary.

Do not add automatic LLM activation.

Draft and active states must be visually distinct.

---

# 12. Evidence Page

Use this page to display reproducible engineering evidence.

Show:

```text
Mapping benchmark
Tag quality
Metadata contract
Summary faithfulness
Artifact consistency
Field operations
Schema localization
Replay
Runtime equivalence
Package fault injection
Performance
Concurrency
Downstream contracts
CI status
```

Every metric card or row must include:

```text
status
dataset version
dataset hash
commit SHA
reproduction command
claim boundary
```

Do not present:

```text
package verification = semantic mapping correctness
```

External blind status must remain visible when it is `not_run`.

---

# 13. Overview Page

Keep the overview intentionally simple.

Required content:

- one primary “New conversion” action;
- recent tasks;
- pending reviews;
- current service health;
- current backend version;
- latest evidence gate status.

Do not display full reports on the overview.

Do not recreate the current “everything on one page” layout.

---

# 14. Visual Design System

Use a calm, enterprise-grade technical visual language.

## Style

```text
Neutral enterprise workspace
Technical precision
High information clarity
Low visual noise
```

## Colors

Use:

- neutral near-white page background;
- white working surfaces;
- restrained blue primary accent;
- green for success;
- amber for review required;
- red only for blocking failure;
- gray-blue for neutral information.

Avoid:

- gradients;
- glassmorphism;
- neon;
- decorative AI imagery;
- strong shadows;
- excessive border radius;
- card-inside-card layouts;
- every row as an independent card.

## Typography

Use:

```text
Inter, Source Sans 3, or system sans-serif
```

Use monospace only for:

- JSON;
- IDs;
- paths;
- hashes;
- versions;
- source values.

Body text:

```text
14–16px
```

Use a restrained type scale.

## Spacing

Use an 8px spacing system.

Recommended:

```text
8
12
16
24
32
40
```

## Components

Prefer:

- tables;
- split panes;
- grouped lists;
- tabs;
- accordions;
- drawers;
- compact status badges;
- inline alerts;
- sticky action bars.

Avoid excessive standalone dashboard cards.

## Status semantics

Every status must include text, not color alone.

Use consistent vocabulary:

```text
Completed
Review required
Failed
Running
Pending
Blocked
Unmapped
Verified
Unverified
```

---

# 15. Responsive Behavior

Primary target is desktop.

Support:

```text
1440px
1280px
1024px
```

At narrower desktop widths:

- collapse sidebar;
- keep the stepper readable;
- stack sticky summary below main content when required;
- make large tables horizontally scrollable;
- preserve primary action visibility.

Do not optimize for mobile-first.

Provide a usable read-only mobile fallback only if inexpensive.

---

# 16. Accessibility Requirements

Implement:

- semantic HTML;
- keyboard navigation;
- visible focus states;
- sufficient color contrast;
- labels for all controls;
- accessible status text;
- accessible tabs;
- accessible accordions;
- accessible dialogs and drawers;
- no color-only meaning;
- no hover-only information;
- logical heading hierarchy;
- error messages connected to fields;
- reduced-motion consideration.

Mapping review should support keyboard-friendly navigation.

---

# 17. Frontend Architecture

Refactor the current large application component into route-level pages and focused modules.

Recommended structure:

```text
frontend/src/
  app/
    App.tsx
    router.tsx
    providers.tsx

  layouts/
    AppShell.tsx
    WorkflowLayout.tsx
    TaskDetailLayout.tsx

  pages/
    overview/
    conversion/
    tasks/
    task-detail/
    review/
    schemapacks/
    evidence/
    settings/

  components/
    navigation/
    workflow/
    status/
    tables/
    forms/
    mapping/
    validation/
    content/
    package/
    lineage/
    evidence/
    feedback/

  hooks/
  services/
  state/
  styles/
  types/
  utils/
```

Use the current project’s conventions where sensible.

Do not introduce unnecessary complexity.

A routing library may be added if justified.

Keep:

- server state;
- page state;
- form state;

clearly separated.

Avoid one giant global store.

Centralize:

- API errors;
- loading behavior;
- status formatting;
- task polling;
- clipboard utilities;
- date formatting;
- ID truncation;
- contract compatibility warnings.

---

# 18. Backend Contract Preservation

Before changing UI:

1. inspect `frontend/src/api.ts`;
2. inspect frontend types;
3. inspect OpenAPI;
4. identify all existing frontend API usage;
5. map every existing action into the new UI.

Do not change backend endpoints merely to simplify the frontend unless absolutely necessary.

When a missing backend capability prevents a truthful UI:

- do not fake it;
- disable the action;
- show an explanatory tooltip;
- document the limitation.

---

# 19. Loading, Empty, Error, and Partial States

Every page must handle:

```text
loading
empty
ready
partial
review required
failed
offline
```

Required examples:

- no imported UIR;
- no SchemaPacks;
- no tasks;
- no reviews;
- task still running;
- task completed without package;
- package verification failed;
- Topic 11 unavailable;
- backend unavailable;
- evidence report missing;
- deprecated SchemaPack;
- invalid UIR;
- conflicting configuration.

Error messages should include, when available:

```text
error code
stage
path
retryability
operator action
```

Do not expose raw stack traces.

---

# 20. Testing Requirements

Preserve all existing frontend tests.

Add tests for:

## Navigation

- sidebar navigation;
- active route;
- collapsed navigation;
- direct route loading.

## Conversion wizard

- invalid UIR blocks progression;
- valid UIR enables next step;
- SchemaPack selection;
- configuration summary;
- advanced settings;
- review step;
- execution submission;
- saved state between steps.

## Task result

- completed state;
- review-required state;
- failed state;
- package verified;
- package failed;
- replay action;
- missing report.

## Mapping review

- candidate selection;
- target selection;
- evidence rendering;
- deterministic versus LLM label;
- accept/reject/defer actions where APIs exist;
- keyboard navigation.

## Accessibility

- labeled controls;
- tab roles;
- dialog roles;
- status text;
- focus behavior.

## Regression

- existing External UIR workflows;
- existing lineage view;
- existing Schema Draft Lab;
- existing package manifest view;
- existing evidence data.

Run:

```bash
npm test
npm run build
```

Also run repository-level verification required by the project.

---

# 21. Visual Verification

After implementation:

1. run the frontend locally;
2. capture screenshots for:
   - Overview;
   - New Conversion Step 1;
   - New Conversion Step 2;
   - New Conversion Step 3;
   - New Conversion Step 4;
   - Execution;
   - Task Overview;
   - Mapping Review;
   - Package Verification;
   - Tasks;
   - SchemaPacks;
   - Evidence;
3. inspect at:
   - 1440px;
   - 1280px;
   - 1024px;
4. fix:
   - overflow;
   - clipped controls;
   - inconsistent spacing;
   - inaccessible contrast;
   - broken empty states;
   - oversized cards;
   - duplicated information;
   - action hierarchy problems.

Do not claim visual verification without actual rendered screenshots.

---

# 22. Implementation Order

Use this order:

```text
1. Audit current frontend workflows
2. Define route and component map
3. Add application shell and navigation
4. Build New Conversion workflow
5. Build execution state
6. Build Task Detail
7. Build Mapping Review
8. Build Tasks
9. Build SchemaPacks
10. Build Evidence
11. Migrate remaining existing capabilities
12. Remove obsolete duplicate UI
13. Add tests
14. Run visual QA
15. Run full repository verification
16. Document the result
```

Do not delete the old UI until feature-equivalence is proven.

---

# 23. Acceptance Criteria

The redesign is complete only when:

1. The primary conversion flow is step-based and easy to understand.
2. A user can move from UIR input to verified package without navigating a dense all-in-one page.
3. Existing backend contracts remain compatible.
4. Existing frontend capabilities remain accessible.
5. The current giant App component has been decomposed.
6. Task execution states are truthful.
7. Mapping evidence is readable without opening raw JSON.
8. Validation issues are grouped and actionable.
9. Content and package outputs are clearly separated.
10. Package verification is visually prominent.
11. LLM suggestions cannot be mistaken for automatic mappings.
12. Topic 5 boundaries remain intact.
13. Desktop layouts work at 1440px, 1280px, and 1024px.
14. Accessibility basics pass.
15. All frontend tests pass.
16. Frontend production build passes.
17. Repository verification still passes.
18. Screenshots prove visual QA.
19. No fake backend capability was added.
20. The final implementation report contains no unsupported claims.

---

# 24. Required Final Report

At completion, provide:

```text
branch name
final commit SHA
design summary
route map
component map
changed files
removed obsolete components
backend contract changes, if any
screenshots
commands executed
frontend test result
frontend build result
repository verification result
accessibility checks
known limitations
remaining follow-up work
```

Do not end after presenting mockups.

Implement the selected design, verify it, and return the completed result.
