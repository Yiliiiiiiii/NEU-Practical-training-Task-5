# Product

## Register

product

## Users

SchemaPack Agent is used by engineers, data product owners, and evaluation reviewers who need to convert upstream UIR documents into schema-driven, auditable output packages. They work in a focused desktop environment, often comparing structured JSON, mappings, validation reports, Markdown output, and downloadable package evidence in one session.

## Product Purpose

The product turns the backend conversion pipeline into an inspectable workbench. A user should be able to import a UIR document, register or select a Target Schema and Mapping Template, create a task, review mappings, run conversion, inspect reports, generate a package, and download `standard_package.zip` without dropping into Swagger or the terminal.

Success means the UI demonstrates the full P0 loop clearly:

```text
UIR -> Schema -> Template -> Task -> Mapping -> Review -> Convert -> Reports -> Package -> Download
```

## Brand Personality

Calm, literate, exacting.

The product should feel like a document editor blended with a conversion console: readable, deliberate, and trustworthy. It should favor clear status evidence and provenance over spectacle.

## Anti-references

- No marketing landing page or oversized hero section.
- No decorative dashboard theater with meaningless charts.
- No heavy sci-fi dark mode, neon gradients, or full-screen command center styling.
- No fake data that hides API failures during the final Phase 8 build.
- No cramped admin table that makes JSON, Markdown, and reports painful to read.

## Design Principles

1. Make the pipeline legible. Every stage should show what is ready, what is blocked, and what action is available next.
2. Treat documents as first-class. JSON, Markdown, reports, and trace output need comfortable reading surfaces.
3. Preserve trust. Status chips, errors, report summaries, and download hashes should be visible where decisions happen.
4. Keep controls predictable. Use standard buttons, tabs, forms, tables, textareas, and download links with consistent behavior.
5. Prefer real workflow over decoration. Motion and visual polish should clarify state transitions, not distract from conversion evidence.

## Accessibility & Inclusion

Target WCAG 2.1 AA for text contrast, focus visibility, keyboard navigation, and reduced motion. The interface must remain readable on desktop and mobile widths, with no text overflow in primary controls or cards. Motion must be brief and disabled or reduced when `prefers-reduced-motion` is enabled.
