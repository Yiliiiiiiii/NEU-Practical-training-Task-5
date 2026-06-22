# Design

## Overview

SchemaPack Agent uses a document-workbench interface: a compact application shell, a persistent workflow rail, and reading-first panels for JSON, Markdown, mappings, reports, trace events, and package evidence.

The visual goal is closer to a document editor than a data command center. The interface should feel quiet, exact, and useful for repeated inspection.

## Visual System

### Color

Use a restrained light theme with neutral document surfaces and a small semantic palette.

Recommended CSS tokens:

```css
:root {
  --bg: oklch(0.975 0.004 250);
  --surface: oklch(0.995 0.002 250);
  --surface-2: oklch(0.955 0.006 250);
  --ink: oklch(0.245 0.018 255);
  --muted: oklch(0.48 0.018 255);
  --line: oklch(0.87 0.009 250);
  --accent: oklch(0.53 0.12 222);
  --accent-weak: oklch(0.93 0.035 222);
  --success: oklch(0.52 0.13 152);
  --warning: oklch(0.67 0.14 72);
  --danger: oklch(0.58 0.18 28);
  --focus: oklch(0.65 0.16 222);
}
```

Use accent color for primary actions, selected navigation, and active stage indicators. Use semantic colors only for status and report severity. Avoid decorative gradients.

### Typography

Use one high-quality UI sans stack for the product surface:

```css
font-family: ui-sans-serif, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
```

Use a monospace stack for JSON, hashes, IDs, and Markdown previews:

```css
font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
```

Type scale should stay compact and stable:

- Page title: 24px / 32px, 650 weight.
- Section title: 16px / 24px, 650 weight.
- Body: 14px / 22px.
- Metadata and table text: 13px / 20px.
- Code: 12px / 19px.

Do not use fluid font sizes.

### Layout

The application shell has three zones:

1. Header: product name, API base status, current task, primary run action.
2. Left rail: pipeline stages and page navigation.
3. Main workbench: one or two panels depending on the screen.

Desktop layout should be dense but not cramped. Mobile layout collapses the rail into a top stage bar and stacks panels vertically.

Cards are allowed for repeated task rows, report summaries, and framed tools only. Avoid nested cards.

### Components

Core components:

- App shell and workflow rail.
- Stage progress row with `pending`, `ready`, `blocked`, `running`, and `done` states.
- Textarea-based JSON editor with validation feedback.
- File import control.
- Data table for tasks and mappings.
- Mapping review controls using selects and icon buttons.
- Tabs for output previews and reports.
- Toast/status region for action results.
- Download panel with package ID, ZIP hash, and report summaries.

Each interactive control needs visible hover, focus, disabled, loading, and error states.

### Motion

Use short state-based motion only:

- 120-180ms panel transitions.
- Progress stage state changes.
- Button loading feedback.
- Toast enter/exit.

No decorative page-load choreography. Respect `prefers-reduced-motion`.

## Phase 8 Screen Direction

### Dashboard

Show the task list with status, document, schema, template, and updated time. Include quick actions for import and opening task detail.

### Import And Setup

Provide three adjacent setup panels:

1. UIR import from demo sample, pasted JSON, or file.
2. Target Schema import from demo sample, pasted JSON, or file.
3. Mapping Template import from demo sample, pasted JSON, or file.

After import, allow task creation from selected document/schema/template.

### Mapping Review

Display candidates and mappings in a readable table. Review-required rows should be visually prominent but not alarming. Let users confirm mappings or change target field IDs.

### Task Detail

Show task metadata, stage actions, canonical preview, output tabs, validation report, consistency report, mapping report, and trace.

### Package

Show package generation action, package response, validation/consistency summary, ZIP SHA-256, and download button.

## Quality Bar

The Phase 8 UI is accepted only if it runs against the real backend API, builds successfully, and supports the complete demo workflow using `examples/demo`.
