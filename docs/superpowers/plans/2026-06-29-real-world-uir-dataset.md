# Real-World UIR Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible official-public-document pipeline that produces at least 16 existing-schema-compatible UIR files and evaluates them through the current SchemaPack API and package verifier.

**Architecture:** Keep acquisition and extraction outside the backend in focused scripts. A shared helper owns stable IDs, UIR assembly, manifest/report I/O, and privacy checks; format-specific extractors return normalized blocks. The build, validation, and evaluation commands orchestrate those helpers without changing the existing conversion pipeline.

**Tech Stack:** Python 3.13, requests, BeautifulSoup4/lxml, PyMuPDF, python-docx, Pydantic, FastAPI/httpx, pytest, Ruff.

---

## File Map

- `scripts/real_world_uir_common.py`: shared models, paths, hashes, atomic JSON/report I/O, stable IDs and UIR assembly.
- `scripts/collect_real_world_sources.py`: bounded HTTP collection and manifest state transitions.
- `scripts/extract_html_to_uir.py`: deterministic HTML title/paragraph/list/table extraction.
- `scripts/extract_pdf_to_uir.py`: text-layer PDF extraction and scanned-PDF detection.
- `scripts/extract_docx_to_uir.py`: optional DOCX paragraph/table extraction.
- `scripts/build_real_world_uir.py`: dispatch formats, build UIR files and extraction reports.
- `scripts/validate_real_world_uir.py`: structural/schema/privacy checks and validation reports.
- `scripts/eval_real_world_uir.py`: live API evaluation and final reports.
- `backend/tests/test_real_world_uir_tools.py`: deterministic unit/integration coverage for all tools.
- `backend/tests/fixtures/real_world/`: small synthetic HTML/PDF/DOCX fixtures generated or stored for tests.
- `examples/real_world/**`: manifest, UIR files, expectation drafts, reports and cache placeholder.
- `docs/real_world_uir_dataset.md`: source scope, reproduction and limitations.
- `backend/requirements.txt`: lightweight extraction dependencies.
- `.gitignore`: ignore real-world raw cache and downloaded packages.
- `README.md`: link to the real-world dataset workflow.

### Task 1: Dataset Skeleton and Shared UIR Builder

**Files:**
- Create: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/real_world_uir_common.py`
- Create: `examples/real_world/README.md`
- Create: `examples/real_world/sources/source_manifest.json`
- Create: `examples/real_world/raw_cache/.gitkeep`
- Create: `examples/real_world/uir/{policy,procurement,contract,meeting,general,_rejected}/.gitkeep`
- Create: `examples/real_world/expectations_draft/{policy,procurement,contract,meeting,general}/.gitkeep`
- Create: `examples/real_world/reports/.gitkeep`

- [ ] **Step 1: Write the failing shared-builder test**

```python
def test_build_uir_matches_existing_schema():
    common = load_script("real_world_uir_common")
    uir = common.build_uir(
        source={"source_id": "real_policy_001", "doc_type": "policy_doc"},
        title="公开政策",
        blocks=[{"type": "heading", "level": 1, "text": "公开政策"}, ...],
        source_bytes=b"official",
        retrieved_at="2026-06-29T00:00:00+08:00",
        source_format="html",
        extraction_method="beautifulsoup",
    )
    assert UIRDocument.model_validate(uir).doc_id == "real_policy_001"
    assert uir["metadata"]["source_sha256"] == hashlib.sha256(b"official").hexdigest()
```

- [ ] **Step 2: Run the test and verify RED**

Run: `backend\.venv\Scripts\python.exe -m pytest tests/test_real_world_uir_tools.py::test_build_uir_matches_existing_schema -v` from `backend`.

Expected: FAIL because `scripts/real_world_uir_common.py` does not exist.

- [ ] **Step 3: Implement the minimum shared builder**

Implement `build_uir`, `read_json`, `write_json_atomic`, `sha256_bytes`, `slugify`,
`block_id`, `dataset_paths`, and Markdown table escaping. The builder must emit only
fields accepted by `UIRDocument`; traceability fields belong under `metadata`.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the same pytest command. Expected: PASS.

### Task 2: HTML Extraction

**Files:**
- Modify: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/extract_html_to_uir.py`

- [ ] **Step 1: Add failing HTML behavior tests**

```python
def test_html_extractor_emits_heading_list_table_and_paragraph():
    result = extract_html(html_bytes, source_url="https://example.gov.cn/doc")
    assert result.title == "示例政策"
    assert [block["type"] for block in result.blocks] == [
        "heading", "paragraph", "list", "table"
    ]
    assert result.blocks[-1]["attributes"]["rows"] == [
        {"field": "项目", "value": "金额"},
        {"field": "A", "value": "100"},
    ]
```

Also test removal of script/nav/footer content and explicit metadata labels.

- [ ] **Step 2: Run tests and verify RED**

Expected: import failure for the missing extractor.

- [ ] **Step 3: Implement deterministic extraction**

Use `BeautifulSoup(..., "lxml")`; select `article`, `main`, common content IDs/classes,
then `body`; remove non-content nodes; walk headings, paragraphs, lists and tables in
DOM order; normalize whitespace; cap duplicate text; return an `ExtractionResult`.

- [ ] **Step 4: Run tests and verify GREEN**

Run the focused HTML test set. Expected: all PASS.

### Task 3: PDF and DOCX Extraction

**Files:**
- Modify: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/extract_pdf_to_uir.py`
- Create: `scripts/extract_docx_to_uir.py`

- [ ] **Step 1: Add failing PDF/DOCX tests**

```python
def test_pdf_extractor_preserves_page_anchors(tmp_path):
    pdf_path = make_text_pdf(tmp_path)
    result = extract_pdf(pdf_path.read_bytes())
    assert len(result.blocks) >= 3
    assert result.blocks[0]["source_anchor"]["page"] == 1

def test_pdf_extractor_skips_scanned_pdf(tmp_path):
    result = extract_pdf(make_image_only_pdf(tmp_path).read_bytes())
    assert result.status == "skipped"
    assert result.reason == "unsupported_scanned_pdf"
```

Add a DOCX test for Heading 1, paragraphs and a two-column table.

- [ ] **Step 2: Run tests and verify RED**

Expected: missing extractor modules.

- [ ] **Step 3: Implement the extractors**

PyMuPDF opens bytes, counts non-whitespace characters per page, skips documents below
the text threshold, preserves page anchors, and uses font size/style only for conservative
heading detection. python-docx maps heading styles and tables without inventing fields.

- [ ] **Step 4: Run tests and verify GREEN**

Expected: PDF and DOCX tests PASS.

### Task 4: Bounded Source Collection

**Files:**
- Modify: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/collect_real_world_sources.py`

- [ ] **Step 1: Add failing collector tests**

Use an injected/fake requests session to verify:

- successful content is cached with the expected SHA-256;
- oversized content is rejected before writing;
- HTML login/verification pages are skipped;
- manifest updates are atomic and keep unrelated items unchanged;
- only `http` and `https` URLs are accepted.

- [ ] **Step 2: Run tests and verify RED**

Expected: missing collector.

- [ ] **Step 3: Implement collection**

Expose `collect_manifest(manifest_path, cache_dir, session, timeout, max_bytes,
source_ids)` and a CLI. Stream responses, identify extension from manifest/Content-Type,
write through a temporary file, and record `retrieved_at`, `source_sha256`,
`cached_path`, `http_status`, `status`, and structured failure reason.

- [ ] **Step 4: Run tests and verify GREEN**

Expected: collector tests PASS.

### Task 5: Build Orchestration and Reports

**Files:**
- Modify: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/build_real_world_uir.py`
- Create: `examples/real_world/reports/extraction_report.json`
- Create: `examples/real_world/reports/extraction_report.md`

- [ ] **Step 1: Add a failing mixed-format build test**

Build a temporary manifest with one HTML and one text PDF cache item. Assert two UIR
files are created in the doc-type directories, statuses change to `extracted`, and JSON
and Markdown reports have identical totals.

- [ ] **Step 2: Run and verify RED**

Expected: missing orchestrator.

- [ ] **Step 3: Implement format dispatch and reporting**

Expose `build_dataset(manifest_path, cache_dir, uir_dir, reports_dir, source_ids)`.
Do not download; consume cache only. Catch errors per source, write rejection records,
and atomically update manifest/report files.

- [ ] **Step 4: Run and verify GREEN**

Expected: build tests PASS.

### Task 6: UIR Validation, Privacy Checks, and Rejection

**Files:**
- Modify: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/validate_real_world_uir.py`
- Create: `examples/real_world/reports/validation_report.json`
- Create: `examples/real_world/reports/validation_report.md`

- [ ] **Step 1: Add failing validation tests**

Cover a valid file, missing traceability metadata, duplicate/empty blocks, invalid URL,
mojibake, phone number, identity-card number, personal email, bank-card number, malformed
table rows, low-confidence hint without `review_required`, and an attempted move outside
the dataset root.

- [ ] **Step 2: Run and verify RED**

Expected: missing validator.

- [ ] **Step 3: Implement validation**

Expose `validate_uir_data`, `scan_sensitive_information`, `validate_dataset`, and safe
move helpers. Validate with `UIRDocument.model_validate`; keep every finding as
`{"code", "path", "message"}`; move only when both resolved paths are descendants of the
configured UIR root.

- [ ] **Step 4: Run and verify GREEN**

Expected: validation tests PASS and no fixture leaves its temporary root.

### Task 7: API Evaluation

**Files:**
- Modify: `backend/tests/test_real_world_uir_tools.py`
- Create: `scripts/eval_real_world_uir.py`

- [ ] **Step 1: Add failing evaluation-client tests**

Use `httpx.MockTransport` to model import, task creation/execution, report endpoints,
package metadata/download and verifier report. Assert procurement maps to general,
review/high-risk counts aggregate, API key is sent but absent from output, and one failed
case does not stop later cases.

- [ ] **Step 2: Run and verify RED**

Expected: missing evaluator.

- [ ] **Step 3: Implement evaluator**

Expose `evaluate_dataset` with injected `httpx.Client`, schema/template mapping and report
writers. Treat `completed` and `review_required` task statuses as execution success when
package verification passes. Save packages outside the example dataset under
`reports/real_world_packages/`.

- [ ] **Step 4: Run and verify GREEN**

Expected: evaluation tests PASS.

### Task 8: Dependencies, Ignore Rules, and Documentation

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `.gitignore`
- Modify: `README.md`
- Create: `docs/real_world_uir_dataset.md`

- [ ] **Step 1: Add dependency/import smoke assertions**

Add a parametrized test importing `requests`, `bs4`, `fitz`, `docx`, and `httpx`.

- [ ] **Step 2: Run and verify current missing dependencies**

Expected: at least one import fails before dependency installation.

- [ ] **Step 3: Add pinned dependencies and documentation**

Document source policy, supported/unsupported formats, deterministic generation, privacy
rules, sample counts, badcases, collection/build/validation/evaluation commands,
limitations, and the fact that the main system still starts from UIR.

- [ ] **Step 4: Install and verify imports**

Run: `backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`.
Then rerun the smoke test; expected PASS.

### Task 9: Five-Source Pilot

**Files:**
- Modify: `examples/real_world/sources/source_manifest.json`
- Create: five UIR JSON files under `examples/real_world/uir/`
- Modify: extraction/validation reports

- [ ] **Step 1: Select and verify sources**

Choose five official public URLs: three HTML and two text PDFs. Verify HTTP status,
official-domain ownership, content type, public accessibility, and absence of personal
sensitive information before adding them to the manifest.

- [ ] **Step 2: Collect, build, and validate**

Run:

```powershell
backend\.venv\Scripts\python.exe scripts\collect_real_world_sources.py
backend\.venv\Scripts\python.exe scripts\build_real_world_uir.py
backend\.venv\Scripts\python.exe scripts\validate_real_world_uir.py
```

Expected: five extracted and five validated samples.

- [ ] **Step 3: Run live API evaluation**

Start the backend using its isolated test storage/database configuration, run the evaluator,
and verify each sample imports, executes, yields reports, downloads a ZIP and has a verifier
report. Fix tool defects through a new failing regression test before changing code.

- [ ] **Step 4: Check the pilot gate**

Proceed only if all five import and execute and at least four packages verify successfully.

### Task 10: Expand to the 16-Sample Minimum

**Files:**
- Modify: source manifest, UIR directories and reports

- [ ] **Step 1: Add eleven verified official sources**

Reach policy 5, procurement 5, meeting 3 and general 3. Include at least five natural
badcases spanning date, amount, subject, heading hierarchy and table complexity.

- [ ] **Step 2: Re-run collection/build/validation**

Expected: at least 16 validated UIR files and exact manifest/report distribution.

- [ ] **Step 3: Re-run API evaluation**

Expected: every validated UIR imports; failures have explicit reasons; package verifier
pass rate is at least 80%.

- [ ] **Step 4: Generate final reports**

Create `reports/real_world_eval_report.json`, `reports/real_world_eval_report.md`, and
downloaded packages. Ensure Markdown metrics are derived from the JSON report.

### Task 11: Full Verification and Requirement Audit

**Files:**
- Modify only files required by regression fixes

- [ ] **Step 1: Run dataset tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_real_world_uir_tools.py -v`
from the repository root. Expected: all PASS.

- [ ] **Step 2: Run backend tests and Ruff**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
backend\.venv\Scripts\python.exe -m ruff check .
```

from `backend`. Expected: zero failures/errors.

- [ ] **Step 3: Run frontend and project verification**

Run:

```powershell
npm.cmd run build
backend\.venv\Scripts\python.exe scripts\verify_all.py --include-evaluator
```

Expected: exit code 0.

- [ ] **Step 4: Audit every acceptance criterion**

Compare the current filesystem and fresh reports against Sections 23, 27 and 30 of the
guidance document. Confirm all named deliverables exist, source metadata is present,
HTML/PDF/scanned-PDF behavior is proven, 16 samples exist, reports explain all failures,
and package verification is at least 80%. Any uncovered gap returns to a failing test and
implementation cycle.
