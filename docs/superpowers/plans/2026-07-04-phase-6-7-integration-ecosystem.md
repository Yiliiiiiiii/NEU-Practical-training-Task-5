# Phase 6-7 Integration Ecosystem Implementation Plan

> **Historical plan:** CLI, Python SDK, Adapter scaffold, and consumer contracts are implemented; Webhook remains an optional non-implemented item. Current status: [`../../project_status.md`](../../project_status.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add versioned downstream consumer contracts plus a usable CLI, Python SDK, and safe adapter scaffold without changing the existing package format.

**Architecture:** Contract manifests describe exported record or package requirements. A shared verifier loads a package through the existing checksum-safe package reader, invokes the matching existing exporter in a temporary directory, validates required field paths, and emits JSON/Markdown reports. Integration tools call only public HTTP APIs; generated adapter code remains inert until explicitly reviewed and registered.

**Tech Stack:** Python 3.12, Pydantic/FastAPI schemas already in the repo, `httpx`, `argparse`, JSON/JSONL/CSV, pytest.

---

### Task 1: Consumer Contract Registry

**Files:**
- Create: `contracts/rag_corpus_contract_v1.json`
- Create: `contracts/training_corpus_contract_v1.json`
- Create: `contracts/structured_csv_contract_v1.json`
- Create: `contracts/package_contract_v1_1.json`
- Test: `backend/tests/test_consumer_contract_verifier.py`

- [ ] Write a failing test that loads all manifests and requires unique `contract_id`, semantic `version`, an `artifact_type`, and non-empty `required_fields` or `required_package_files`.
- [ ] Run `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_consumer_contract_verifier.py -q` and confirm the manifests are missing.
- [ ] Add four manifests matching current exporter/package output; keep all additions backward compatible.
- [ ] Re-run the test and confirm it passes.

### Task 2: Unified Consumer Verifier

**Files:**
- Create: `scripts/consumer_contract.py`
- Create: `scripts/verify_consumer_contract.py`
- Test: `backend/tests/test_consumer_contract_verifier.py`

- [ ] Add failing tests for one package, field-path failure, and recursive batch verification.
- [ ] Confirm failures are caused by the absent verifier.
- [ ] Implement contract loading, safe exporter dispatch, record validation, package artifact validation, JSON/Markdown reports, and aggregate `consumer_contract_pass_rate`.
- [ ] Run the focused tests and require `>= 0.95` on generated production-like packages.

### Task 3: Python SDK and Unified CLI

**Files:**
- Create: `sdk/python/schemapack_client/__init__.py`
- Create: `sdk/python/schemapack_client/client.py`
- Create: `sdk/python/schemapack_client/models.py`
- Create: `scripts/schemapack_cli.py`
- Test: `backend/tests/test_schemapack_client.py`
- Test: `backend/tests/test_schemapack_cli.py`

- [ ] Write failing `httpx.MockTransport` SDK tests for import, convert, create, execute, download, schemas, and adapters.
- [ ] Implement a context-managed client that supports optional API keys and never logs request bodies or secrets.
- [ ] Write failing CLI parser/dispatch tests for all documented commands.
- [ ] Implement CLI commands by delegating to the SDK; `eval` invokes the consumer verifier and returns non-zero on gate failure.
- [ ] Run focused tests and an actual External UIR to Package CLI workflow against the local API.

### Task 4: Adapter Scaffold

**Files:**
- Create: `templates/adapter_plugin/adapter.py`
- Create: `templates/adapter_plugin/manifest.json`
- Create: `templates/adapter_plugin/fixtures/sample.json`
- Create: `templates/adapter_plugin/tests/test_adapter.py`
- Create: `templates/adapter_plugin/README.md`
- Create: `scripts/scaffold_adapter.py`
- Test: `backend/tests/test_scaffold_adapter.py`

- [ ] Write a failing test that scaffolds a normalized adapter id into an empty destination.
- [ ] Implement deterministic placeholder replacement, destination containment checks, and refusal to overwrite.
- [ ] Verify generated Python compiles and no secret-like values are emitted.

### Task 5: Documentation and Release Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/developer_guide.md`
- Modify: `docs/api_usage_examples.md`
- Modify: `docs/openapi.json`

- [ ] Document contract verification, CLI workflow, SDK usage, and scaffold review/registration boundary.
- [ ] Run `scripts/verify_consumer_contract.py` across real generated packages and save JSON/Markdown reports.
- [ ] Run CLI end-to-end, SDK focused tests, secret scan, `scripts/verify_all.py --check-openapi`, and all frontend tests.
- [ ] Confirm OpenAPI has no drift and the existing package verifier remains green.
