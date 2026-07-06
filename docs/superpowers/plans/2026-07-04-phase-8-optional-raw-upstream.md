# Phase 8 Optional Raw Upstream Implementation Plan

> **Historical plan:** Phase 8 is implemented. Current status: [`../../project_status.md`](../../project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert local raw documents into reviewable External UIR with optional Docling/Unstructured providers while keeping OCR and provider dependencies outside the main service.

**Architecture:** A shared offline module lazily invokes a selected provider, maps extracted content into the existing block-list External UIR dialect, and emits a redacted provenance report. If the optional provider is absent, deterministic text-layer PDF/DOCX/HTML extractors may be used; scanned PDFs remain rejected. Thin provider-specific scripts expose this behavior without adding API routes or default runtime dependencies.

**Tech Stack:** Python 3.13, optional Docling/Unstructured, existing PyMuPDF/python-docx/BeautifulSoup extractors, argparse, pytest.

---

### Task 1: Shared Raw Upstream Conversion

**Files:**
- Create: `scripts/upstream_external_uir.py`
- Test: `backend/tests/test_optional_raw_upstream.py`

- [ ] Write failing tests for text-layer PDF fallback, scanned-PDF rejection, provenance report safety, and Adapter Registry compatibility.
- [ ] Run the focused tests and confirm failure because the shared module is absent.
- [ ] Implement lazy provider invocation, deterministic fallback, block-list conversion, SHA-256 provenance, file-size bounds, and `auto_imported=false`.
- [ ] Re-run focused tests and Ruff.

### Task 2: Provider Entry Scripts

**Files:**
- Create: `scripts/upstream_docling_to_external_uir.py`
- Create: `scripts/upstream_unstructured_to_external_uir.py`
- Test: `backend/tests/test_optional_raw_upstream.py`

- [ ] Write failing parser/CLI tests that require `--out`, `--report`, and optional fallback control.
- [ ] Implement provider-specific wrappers around the shared conversion module.
- [ ] Verify importing either script does not require Docling or Unstructured.

### Task 3: Sample PDF And External UIR Chain

**Files:**
- Create generated fixture: `examples/raw_upstream/sample_policy.pdf`
- Generate: `examples/raw_upstream/sample_policy_external_uir.json`
- Generate: `reports/raw_upstream/sample_policy_report.json`

- [ ] Generate a one-page text-layer PDF fixture and render it to PNG for visual inspection.
- [ ] Run the Docling entry script without Docling installed and confirm deterministic fallback output.
- [ ] Run `schemapack_cli.py convert-external`, import, create-task, execute-task, and download-package on the generated External UIR.
- [ ] Confirm no provider dependency is added to `backend/requirements.txt`.

### Task 4: Documentation And Final Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/developer_guide.md`
- Modify: `docs/api_usage_examples.md`
- Modify: `docs/final_handoff_status.md`

- [ ] Document optional installation, no-OCR behavior, offline-only boundary, and the existing External UIR handoff.
- [ ] Run the optional-upstream focused tests with provider packages absent.
- [ ] Run secret scan, `scripts/verify_all.py --check-openapi`, frontend tests, and the existing regression gates.
