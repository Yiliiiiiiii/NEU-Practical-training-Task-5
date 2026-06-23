# Phase 10 Acceptance Baseline Design

Phase 10 turns the stabilized Phase 9 product into an acceptance-ready baseline. It adds independently verifiable package integrity, replayable task evidence, a frozen mapping evaluation fixture, real-capable LLM fallback plumbing, stronger content organization metadata, and delivery documents. The implementation must keep offline mode deterministic and must not claim a live model call unless credentials are supplied and a real run is executed.

## Goals

1. Provide an external package verifier that can be run outside the package service and rejects unsafe paths, manifest self-reference, missing payloads, extra payloads, byte mismatches, SHA-256 mismatches, invalid JSON, and oversized JSON payloads.
2. Make package completion depend on the same verifier contract used by the CLI, while keeping the verifier report outside the ZIP.
3. Add an LLM fallback path that supports `disabled`, `mock`, and `openai_compatible` modes. The openai-compatible path uses a real HTTP request shape and records model, prompt version, confidence, reason, latency, and failure status. Automated tests use a mock transport; live credentials are optional.
4. Add task replay that creates a child task with `parent_task_id`, copies confirmed candidates and mappings by default, and avoids re-calling the model unless explicitly requested.
5. Create a frozen evaluation fixture with at least 150 gold field mappings and a runner that reports precision, recall, F1, review rate, unmapped required count, and confidence bucket accuracy.
6. Enrich rendered content with document summary, chunk summary, keywords, three-level labels, and upstream entity tags using deterministic local heuristics.
7. Produce delivery documents, frozen OpenAPI JSON, and a one-command demo script.

## Non-Goals

- No model training or fine-tuning.
- No claim that a live cloud model was called in local CI.
- No large frontend redesign in Phase 10.
- No package signature or cryptographic attestation beyond SHA-256 verification.
- No full RAG/business downstream system; only lightweight consumer smoke tests.

## Architecture

The package verifier is a pure file/bytes module under `app.verifiers` plus a CLI under `app.tools`. It depends only on Python stdlib and Pydantic schemas, so it can be reused by tests, the package service, and manual acceptance commands.

The LLM path remains behind `MappingService`. Rule mappings run first. If fallback is enabled, unused candidates and unmapped target fields are passed to `LLMClient`. Suggestions are converted into review-required mappings with audit evidence. Failures degrade to rule output and are recorded in mapping report summary instead of crashing the workflow.

Task replay lives in `TaskService` and exposes `POST /api/v1/tasks/{task_id}/replay`. The default mode copies existing candidates and confirmed mappings into a new child task and sets it to `mapping_completed`, making replay deterministic and model-free.

Evaluation lives under `app.evaluation`. The runner reads `examples/eval/eval_cases.json`, executes the deterministic mapping engine, compares predictions to gold mappings, and writes JSON/Markdown reports. It is separate from demo data to avoid leakage.

Content organization stays deterministic. JSON and chunks renderers derive summaries, keywords, labels, and upstream entities from canonical fields, metadata, block text, and title path. This keeps outputs reproducible offline while making the acceptance package easier to inspect downstream.

## Data Flow

Package flow:

`rendered task -> validation -> consistency -> metadata/config/trace -> manifest -> ZIP -> external verifier -> DB package record -> verifier report outside ZIP`

Replay flow:

`parent task -> copy task refs/options -> copy candidates -> copy confirmed mappings -> child task mapping_completed -> convert/package as usual`

LLM fallback flow:

`rules -> unmapped targets + unused candidates -> LLMClient -> suggestions -> review_required mappings -> mapping_report audit -> manual review`

Evaluation flow:

`examples/eval/eval_cases.json -> MappingEngine -> metrics -> docs/reports/evaluation_report.json|md`

## Error Handling

- Package verifier errors are structured with `code`, `message`, and optional `path`.
- Package service marks task `failed/package_verifier_error` if verifier rejects the ZIP and deletes the unpublished ZIP.
- LLM fallback failures are reported as `llm_status="failed"` and do not fail mapping.
- Replay rejects missing parents and parents without mappings.
- Evaluation rejects malformed fixtures, duplicate gold pairs, and empty gold sets.

## Testing

Backend tests must cover:

- Verifier accepts a real generated package and rejects path traversal, backslashes, extra files, manifest self-reference, byte mismatch, SHA mismatch, missing manifest, invalid JSON, and oversized JSON.
- PackageService uses the external verifier before marking completed and persists the verifier report outside the ZIP.
- LLM fallback disabled/mock/openai-compatible/failure modes.
- Replay creates child tasks with copied mappings and no model call by default.
- Evaluation metrics on the frozen fixture meet the declared threshold.
- Content metadata and chunk labels are populated deterministically.
- API contract inventory includes the new replay and verifier-report routes.

## Acceptance

Phase 10 is accepted when backend coverage gates, frontend gates, lint, build, package verifier CLI, evaluation runner, consumer smoke tests, and documentation generation all pass from a clean checkout. The final report must separate automated evidence from optional live-model evidence.
