# Frontend Chinese Copy Implementation Plan

> **Historical plan:** Preserved as an execution record. See [`../../project_status.md`](../../project_status.md) for current implementation status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use nbl.subagent-driven-development (recommended) or nbl.executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert ordinary user-facing frontend copy to Chinese while preserving professional terms, API fields, IDs, enum values, and report keys.

**Architecture:** Apply surgical copy-only edits in the React workbench. Keep the existing component structure, data flow, and API contracts unchanged; only labels, empty states, table headers, button text, and explanatory UI strings change.

**Tech Stack:** React, TypeScript, Vite.

---

### Task 1: Localize visible workbench copy

**状态**
- [ ] 任务完成

**Dependencies:** None
**Parallelizable:** No (single focused UI surface)

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/ChunkEvidencePanel.tsx`
- Modify: `frontend/src/components/DownstreamReadinessPanel.tsx`
- Modify: `frontend/src/components/KnowledgeComparisonPanel.tsx`
- Modify: `frontend/src/components/MappingEvidencePanel.tsx`
- Modify: `frontend/src/components/PackageManifestPanel.tsx`
- Modify: `frontend/src/components/ValidationIssuePanel.tsx`
- Modify if needed: `frontend/src/components/DownstreamReadinessPanel.test.tsx`

- [ ] Replace ordinary labels/buttons/empty states with Chinese.
- [ ] Keep professional nouns and machine-facing values such as `UIR`, `JSON`, `Schema`, `Template`, `Mapping`, `Review`, `Knowledge Pack`, `ZIP`, `CSV`, `RAG`, `SHA-256`, status enum values, field IDs, file paths, and script names unchanged when they are identifiers or domain terms.
- [ ] Run `npm run build` in `frontend`.
- [ ] Run any affected frontend tests if assertions depend on changed text.

---

**Execution Mode:** inline
