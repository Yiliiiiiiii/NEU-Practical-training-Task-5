# Topic 5 Batch 2 Execution Specification

## Mapping Generalization, Runtime Convergence, and Production Reliability

**Repository:** `Yiliiiiiiii/NEU-Practical-training-Task-5`  
**Reviewed head:** `661ad4480cfe4aa4982def583c83770c1521707a`  
**Target branch:** create `feat/topic5-batch-2-reliability` from the current `main` head  
**Audience:** Codex  
**Execution mode:** inspect, implement, test, generate evidence, and commit. Do not return only a plan.

---

## 1. Mission

Complete the second development batch for Topic 5 while preserving the exact Topic 5 boundary.

This batch has two mandatory purposes:

1. Correct weaknesses found in the Batch 1 implementation and acceptance evidence.
2. Close the largest remaining Topic 5 requirement gap: credible automatic field-mapping performance on a realistic, leakage-resistant benchmark, while making the conversion runtime deterministic, convergent, robust, and independently verifiable.

The production contract remains:

```text
Normalized UIR
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
    -> deterministic contract validation
    -> candidate extraction
    -> source-to-target field mapping
    -> deterministic field operations
    -> canonical document
    -> JSON / Markdown / chunks
    -> Schema and artifact validation
    -> manifest and checksums
    -> standard package
```

The target is a mature Topic 5 conversion service, not a general data-governance platform.

---

## 2. Non-Negotiable Topic 5 Boundary

### 2.1 In scope

- Normalized UIR ingestion.
- Target Schema, metadata template, mapping rules, and content-organization configuration.
- Generic candidate extraction from UIR.
- Source-to-target field mapping.
- Mapping confidence, abstention, and human-review evidence.
- Deterministic rename, merge, split, formatting, and target-type conversion.
- Schema validation and exact issue localization.
- Configurable tags, summaries, keywords, entity passthrough, and source links.
- Internal chunking and a Topic 11 provider adapter.
- Canonical-model-based JSON, Markdown, and chunks.
- Package construction, checksums, verification, replay, and reproducibility.
- One-click downstream export contracts.
- Topic 5 tests, benchmarks, load tests, fault-injection tests, CI, and documentation.

### 2.2 Out of scope

Do not add or absorb any of the following:

- PDF, Word, Excel, image, scan, or OCR parsing.
- Cleaning, de-noising, redaction, or semantic normalization.
- Entity recognition, knowledge-base lookup, entity disambiguation, or entity ID generation.
- Quality scores, quality grades, publication decisions, or automatic routing.
- LLM-as-Judge or governance-fidelity scoring.
- Vector databases, embedding pipelines, retrieval services, or RAG question answering.
- Topic 11 retrieval-quality optimization.
- Self-evolution harnesses or automatic production promotion.
- Multi-agent orchestration, global scheduling, or cross-agent state machines.
- Enterprise SSO, tenant platforms, billing, or organization-wide policy engines.

### 2.3 LLM rule

LLM output may only be:

```text
report-only
or
review-required suggestion
```

It must never:

- count as an automatic deterministic mapping;
- modify production output without explicit review;
- activate a SchemaPack;
- write mapping rules;
- bypass a negative-pair rule;
- bypass Schema or package validation.

---

# 3. Batch 1 Audit Summary

Batch 1 delivered substantial functionality and should be preserved:

- Effective metadata templates.
- Configurable three-level tags.
- Chunk-local quality tags.
- Upstream entity passthrough.
- Deterministic document summaries.
- Topic 11 provider interface.
- Cross-artifact consistency checks.
- Expanded field-operation and localization fixtures.
- Extended lineage and golden-package tests.

However, the following items must be corrected before Batch 2 metrics may be accepted.

---

## 4. Mandatory Batch 1 Corrections

These corrections are **P0**. Implement them before tuning the mapping engine.

## 4.1 Replace proxy metrics with measured metrics

### Current weakness

The Batch 1 gate currently converts a passing component test into values such as:

```text
summary faithfulness = 1.0
source coverage = 1.0
tampering detection rate = 1.0
entity passthrough coverage = 1.0
Topic 11 fallback success rate = 1.0
```

A passing test module proves that assertions passed. It does not itself measure a rate over a declared dataset.

The gate must not derive quantitative metrics from:

```python
1.0 if pytest_passed else 0.0
```

### Required correction

Create real evaluators and machine reports for:

```text
metadata template effectiveness
metadata issue localization
document-summary faithfulness
document-summary source coverage
new-fact violations
artifact-consistency pass rate
Markdown block coverage
chunk-to-source coverage
tampering detection
entity passthrough coverage
invented entity IDs
Topic 11 fallback success
invalid external output acceptance
secret leakage
legacy compatibility
```

Each evaluator must report:

```text
dataset_id
dataset_version
dataset_sha256
commit_sha
case_count
passed_count
metric value
failed cases
reproduction command
claim boundary
```

The Batch 2 gate must read those reports. It must not infer rates from test-module success.

### Required files

Suggested:

```text
scripts/eval_topic5_metadata_contract.py
scripts/eval_topic5_summary_faithfulness.py
scripts/eval_topic5_artifact_consistency.py
scripts/eval_topic5_entity_passthrough.py
scripts/eval_topic5_topic11_adapter.py
```

Fixtures:

```text
eval/topic5_metadata_contract/v2/
eval/topic5_summary_faithfulness/v2/
eval/topic5_artifact_consistency/v2/
eval/topic5_entity_passthrough/v2/
eval/topic5_topic11_adapter/v2/
```

---

## 4.2 Make verification evidence executable, not manually asserted

### Current weakness

The committed verification summary contains manually recorded booleans and counts. Some raw evidence files are empty, and the repository head has no GitHub status checks proving the same commit passed.

### Required correction

Create one cross-platform evidence runner:

```text
scripts/run_topic5_batch_2_verification.py
```

Requirements:

- Use `sys.executable`, not `backend/.venv/Scripts/python.exe`.
- Run on Windows and Linux.
- Capture stdout, stderr, command, return code, duration, and tool versions.
- Refuse to mark a check passed when the command was skipped.
- Record the exact current commit SHA.
- Fail when the working tree is dirty unless `--allow-dirty` is explicitly supplied.
- Store non-empty raw logs.
- Generate `verification_summary.json` from actual subprocess results.
- Exit nonzero when any mandatory command fails.

Add GitHub Actions CI for at least:

```text
backend tests
Ruff
frontend tests
frontend build
OpenAPI drift check
SchemaPack contract gate
Batch 2 acceptance gate
```

No secret-dependent or live LLM test may be required in CI.

---

## 4.3 Freeze independent tag gold; do not rewrite gold to match output

### Current weakness

The existing real-world tag gold was modified in the same implementation batch. Some expected management tags now mirror the new implementation vocabulary. This makes the new score less independent.

### Required correction

Create a new immutable gold version:

```text
eval/topic5_tag_quality/v2/
```

Required process:

1. Copy source UIR references.
2. Write a dataset card defining each tag.
3. Freeze expected labels in a standalone commit before changing tag logic.
4. Record the dataset SHA.
5. Do not modify `v2` after the baseline commit.
6. Any label correction requires `v3`, a written reason, and before/after reports.

Separate:

```text
content-tag semantic evaluation
management-rule correctness
quality-tag localization correctness
```

Management and quality tags are deterministic-rule tests and should not be presented as independent semantic F1 when the expected rule output is generated from the same configuration. Report them as:

```text
rule correctness
trace correctness
scope correctness
```

Content tags may still use precision, recall, and F1 against independent labels.

---

## 4.4 Fix status semantics and unify them

### Current weaknesses

The inline and registered-task pipelines use separate status logic.

The registered-task status evaluator does not take `validation_report.passed` as an input.

The current package-failure condition contains behavior equivalent to:

```text
package failed AND artifact consistency was not false -> failed
```

This allows a package-verifier failure combined with an artifact-consistency failure to become `review_required` rather than `failed`.

### Required correction

Create one service:

```text
backend/app/services/conversion_status_service.py
```

Both execution paths must use it.

Required status rules:

```text
failed:
  unrecoverable runtime exception
  package write failure
  package verifier failure
  strict metadata failure
  strict output assertion failure
  strict Topic 11 provider failure

review_required:
  mapping review items exist
  required source-present target field remains unmapped
  Schema validation failed
  non-strict metadata validation failed
  non-strict output assertion error
  summary faithfulness failed
  artifact consistency failed before packaging
  external provider fell back when policy requires review

completed:
  none of the above conditions exists
```

A package verifier failure is always `failed`.

Add a truth-table test that enumerates all condition combinations.

---

## 4.5 Stop leaking internal runtime state into `content.json.metadata`

### Current weakness

The renderer still constructs an ambiguous metadata object by merging source metadata with the complete internal canonical `doc_meta`. That can expose:

```text
execution snapshots
mapping summaries
transform summaries
metadata reports
internal trace data
```

inside the business-facing `content.json`.

### Required correction

Define explicit output sections:

```json
{
  "source_metadata": {},
  "document_metadata": {},
  "metadata_template": {},
  "document_summary": {},
  "data": {},
  "blocks": [],
  "assets": []
}
```

Do not include internal execution snapshots in `content.json`.

Operational details belong in:

```text
execution_snapshot.json
mapping_report.json
transform_report.json
metadata_template_report.json
content_organization_report.json
```

Maintain a documented legacy compatibility field only if a real consumer test requires it. Mark it deprecated and ensure it contains no secret or internal state.

Add a test that scans `content.json` for forbidden internal keys.

---

## 4.6 Make package verification independent and internally coherent

### Current weaknesses

The current package builder:

1. builds a manifest;
2. verifies;
3. writes `verifier_report.json`;
4. rebuilds the manifest;
5. verifies again;
6. returns the second report but leaves the first report on disk.

The package verifier validates the precomputed consistency report instead of reconstructing and re-running cross-artifact consistency from packaged files.

### Required correction

Redesign package finalization with a non-circular contract.

Recommended model:

```text
content artifacts
    -> content manifest
    -> independent package verification
    -> verifier report
    -> deterministic ZIP
    -> ZIP hash
```

Use one of these explicit designs:

### Preferred design

- `manifest.json` covers all semantic and report artifacts except:
  - `manifest.json`
  - `verifier_report.json`
  - the ZIP itself
- `verifier_report.json` records the manifest hash it verified.
- `OutputPackageMetadata` records:
  - manifest hash
  - verifier-report hash
  - final ZIP hash
- The API returns exactly the verifier report written into the ZIP.
- No stale first-pass report remains.

The verifier must independently load:

```text
canonical.json
content.json
content.md
chunks.jsonl
metadata.json
artifact_consistency_report.json
```

Then re-run `ArtifactConsistencyService` from disk.

It must detect a package where:

- content was changed;
- hashes were recomputed;
- the old consistency report still says passed.

### Atomicity

Build packages in:

```text
packages/.tmp/<package_id>-<random>/
```

Only rename to the final directory after successful verification.

On failure:

- remove the temporary directory;
- do not leave a downloadable ZIP;
- do not overwrite a previously valid package.

---

## 4.7 Require full content coverage in chunks

### Current weakness

The Topic 11 validator currently requires protected blocks to be referenced, but it does not require every non-empty canonical block to be represented by a chunk.

The consistency report currently measures:

```text
percentage of chunks with valid sources
```

not:

```text
percentage of canonical source blocks represented in chunks
```

A provider can therefore drop ordinary paragraphs and still pass.

### Required correction

Add metrics:

```text
chunk_source_validity
canonical_block_coverage
nonempty_block_coverage
protected_block_integrity
duplicate_content_ratio
unexplained_chunk_text_count
```

Default acceptance:

```text
nonempty canonical block coverage = 100%
protected block coverage = 100%
unexplained chunk text count = 0
unknown source block count = 0
```

Allow explicit exclusion only through a deterministic configuration rule containing:

```text
block_id
exclusion_reason
rule_id
```

Topic 5 must not silently drop content.

Update the Topic 11 adapter validator and artifact-consistency verifier.

---

## 4.8 Remove duplicate and contradictory content-organization settings

### Current weakness

The content-organization contract currently contains both:

```text
summary_mode
summary.chunk_mode
```

These can conflict.

### Required correction

Use one source of truth:

```yaml
summary:
  chunk_mode: deterministic
  document_mode: extractive
```

Deprecate the old top-level `summary_mode`.

Backward compatibility behavior:

- accept old input;
- convert it to the new model;
- reject a request when old and new values conflict;
- emit a deprecation warning in the report.

Also fix any path where `doc_id` is passed as `task_id` during internal chunk construction.

Add contract-migration tests.

---

## 4.9 Remove domain-specific automatic normalization from the default Topic 5 core

### Current weakness

The transform service contains hard-coded field and domain behavior such as:

```text
document-type mappings
special array-field lists
organization cleanup field lists
```

Some of this overlaps Topic 4 normalization and makes new SchemaPacks depend on backend code.

### Required correction

The default Topic 5 transform path may perform only transformations declared by:

```text
Target Schema
Mapping Rules
Metadata Template
```

Move field-specific behavior to SchemaPack configuration:

```text
enum_maps
transform_rules
split rules
format rules
defaults
```

Keep legacy behavior only behind:

```text
enable_legacy_transform_heuristics = false
```

Default must be `false`.

Acceptance evidence must run with legacy heuristics disabled.

Do not remove generic type conversion such as ISO date formatting when explicitly required by the target field and mapping rule. Do remove implicit business-domain cleanup that is not declared.

---

## 4.10 Regenerate status documentation from one source

### Current weakness

Current status documents still report old branch names and old test counts, while later appended sections report Batch 1 completion.

### Required correction

Create a single machine source:

```text
reports/topic5_current_status.json
```

Generate these sections from it:

```text
README metric summary
docs/交接/project_status.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/final_handoff_status.md
```

Do not append new status sections to stale documents.

Every generated status must include:

```text
commit SHA
dataset versions and hashes
test counts
gate result
claim boundary
generation command
generation time
```

---

# 5. Batch 2 Core Workstream — Realistic Field-Mapping Benchmark v2

## 5.1 Objective

Provide credible evidence for the Topic 5 requirement:

```text
automatic source-to-target field mapping accuracy >= 85%
difficult items include confidence and support human review
```

The current exact-name generated benchmark remains useful as a smoke test, but it must no longer be the primary acceptance benchmark.

## 5.2 Dataset structure

Create:

```text
eval/topic5_mapping_v2/
├── dataset_card.md
├── manifest.jsonl
├── uir/
├── target_schemas/
├── mapping_rules/
├── gold/
│   ├── dev.jsonl
│   ├── test.jsonl
│   ├── negative_pairs.jsonl
│   ├── required_fields.json
│   └── no_match_cases.jsonl
├── splits/
│   ├── dev.json
│   ├── test.json
│   └── external_blind_manifest.json
└── reports/
```

## 5.3 Dataset requirements

Minimum:

```text
90 documents
6 or more Schema families
15 or more documents per family
300 or more positive field mappings
80 or more explicit negative/no-match decisions
```

Required variety:

- Chinese and English field labels.
- Abbreviations.
- Synonyms not identical to target IDs.
- Long labels.
- Metadata candidates.
- Key-value blocks.
- Tables.
- Paragraph-derived candidates.
- Field order changes.
- Missing optional fields.
- Required fields present under non-obvious labels.
- Multiple date types in one document.
- Budget versus award amount.
- Issuer versus organizer.
- Contact versus attendee.
- Publish date versus effective date.
- Distractor fields with compatible types.
- One-to-many and many-to-one operations only when explicitly declared.
- At least one new Schema not used to tune hard-coded logic.

Restrictions:

- Do not put the target field ID in `attributes.field_name` for the primary evaluation cases.
- Do not copy gold target IDs into candidate hints.
- Do not use `doc_id` special cases.
- Do not generate all splits from one identical template with only numeric variation.
- Direct exact-name cases must be no more than 25% of positive mappings.
- At least 30% of test sources must be held out by source/organization or layout pattern.
- At least one test subset must be Schema-held-out during weight tuning.

## 5.4 Gold freeze process

Use separate commits:

```text
Commit A: add mapping v2 dataset, gold, evaluator, and baseline only
Commit B+: change mapping logic
```

After Commit A:

- calculate all dataset hashes;
- store the baseline report;
- prohibit changes to the v2 UIR, gold, or split files;
- any correction requires a v3 dataset.

Do not ask the mapping engine to generate its own gold.

If independent human annotation is unavailable:

- implement the external blind runner;
- mark external blind status as `not_run`;
- do not claim production blind performance.

## 5.5 Metric definitions

Report automatic and assisted results separately.

### Automatic mapping

Only mappings with:

```text
status = accepted
need_review = false
method != llm_fallback
```

count as automatic predictions.

### Required metrics

```text
auto_exact_field_accuracy
auto_precision
auto_recall
auto_f1
macro_f1_by_schema
required_present_field_recall
review_required_rate
abstention_rate
negative_pair_violation_count
duplicate_source_violation_count
invalid_cardinality_count
test_vs_dev_gap
schema_held_out_f1
```

Define:

```text
auto_exact_field_accuracy =
correct automatically accepted gold target-field decisions
/
all gold positive target-field decisions
```

Do not count a review suggestion as an automatic success.

### Batch 2 targets

On the frozen public test set:

```text
auto_exact_field_accuracy >= 0.85
auto_precision >= 0.90
auto_recall >= 0.85
auto_f1 >= 0.87
macro_f1_by_schema >= 0.82
required_present_field_recall >= 0.95
negative_pair_violation_count = 0
duplicate_source_violation_count = 0
invalid_cardinality_count = 0
review_required_rate <= 0.20
```

If a target is not achieved, report `failed` rather than changing the dataset.

---

# 6. Batch 2 Core Workstream — Mapping Engine v2

## 6.1 Objective

Replace the current greedy score-sorted assignment with a deterministic constrained assignment engine that generalizes beyond exact field names.

## 6.2 Required architecture

Suggested components:

```text
CandidateExtractionService
FieldDescriptorService
MappingFeatureServiceV2
MappingConstraintService
GlobalAssignmentSolver
MappingConfidenceCalibrator
MappingDecisionService
```

## 6.3 Generic field descriptors

For every target field, construct a descriptor from:

```text
field_id
name
display_name
aliases
description
type
required
enum values
format constraints
parent path
SchemaPack mapping rules
```

For every candidate, construct a descriptor from:

```text
source_name
display_name
source path
inferred type
value shape
section title path
block type
neighbor labels
source evidence type
source metadata
```

Do not use document-family constants in core code.

## 6.4 Configurable feature policy

Move weights and evidence priorities out of hard-coded domain dictionaries.

Extend mapping rules with a strict section such as:

```yaml
scoring:
  lexical_weight: 0.25
  alias_weight: 0.20
  type_weight: 0.15
  value_shape_weight: 0.10
  path_weight: 0.10
  context_weight: 0.10
  source_quality_weight: 0.10

evidence_weights:
  metadata: 0.80
  key_value: 0.85
  table: 0.90
  block: 0.70
```

SchemaPack-specific evidence types may be declared by configuration.

Unknown evidence types must use a documented neutral default or be rejected in strict mode.

## 6.5 Constraint model

Support:

```text
one-to-one
one-to-many when explicitly allowed
many-to-one through an explicit merge rule
source reuse only when explicitly allowed
required field priority
blocked source-target pairs
type incompatibility
field-specific minimum score
```

Blocked pairs must be removed from the candidate graph. A blocked candidate must not mark the target as resolved and must not prevent a different valid candidate from being selected.

## 6.6 Real global assignment

Do not call a greedy sorted loop “global assignment.”

Implement deterministic maximum-weight bipartite assignment or min-cost flow.

Requirements:

- stable tie-breaking;
- no dependence on dictionary iteration order;
- deterministic output across platforms;
- explicit dummy nodes for abstention;
- blocked edges excluded;
- review and auto-accept decisions applied after assignment;
- assignment trace retained.

## 6.7 Confidence calibration

Current weighted scores are not calibrated probabilities.

Add a deterministic calibrator fitted only on the dev split.

Permitted approaches:

```text
isotonic regression
Platt/logistic calibration
bin-based monotonic calibration
```

Store calibration parameters as a versioned artifact.

Report:

```text
Brier score
expected calibration error
reliability bins
precision-coverage curve
```

Set thresholds from dev only, freeze them, then run test.

## 6.8 Abstention and review

Required decisions:

```text
accepted
review_required
unmapped
blocked
```

A low-confidence item must abstain rather than force an incorrect mapping.

Each review item must include:

```text
top candidate
top alternatives
calibrated confidence
score margin
feature trace
risk flags
negative-pair checks
review reason
source backlinks
```

LLM suggestions must remain separate and must not alter automatic metrics.

## 6.9 Required regression tests

- Greedy counterexample where optimal assignment differs.
- Valid candidate survives a blocked alternative.
- Deterministic tie.
- Source reuse rejected by default.
- Explicit source reuse allowed.
- Merge cardinality allowed only by rule.
- Schema-held-out descriptors.
- Threshold freeze.
- LLM suggestion excluded from automatic metrics.
- Required field abstention.
- Exact, alias, type, value-shape, and context evidence.
- No `doc_id` rules.
- No target-ID leakage from UIR attributes.

---

# 7. Batch 2 Core Workstream — One Conversion Engine for Both APIs

## 7.1 Objective

Eliminate pipeline drift between:

```text
Topic5ConversionService
TaskExecutionService
```

## 7.2 Required design

Create a pure service:

```text
backend/app/services/topic5_conversion_engine.py
```

Recommended interface:

```python
convert(
    *,
    uir: UIRDocument,
    target_schema: TargetSchema,
    metadata_template: MetadataTemplateConfig | None,
    mapping_rules: MappingTemplate,
    content_organization: ContentOrganizationOptions,
    execution_options: Topic5ExecutionOptions,
    output_assertions: ConversionAssertionConfig | None,
    engine_context: ConversionEngineContext,
) -> ConversionEngineResult
```

The engine must not:

- write files;
- access the database;
- construct HTTP responses;
- mutate global configuration;
- create ZIP files.

It returns:

```text
canonical
rendered artifacts
mapping report
transform report
metadata report
validation report
content-organization report
summary
artifact-consistency report
status inputs
semantic fingerprints
```

The inline service and task service become adapters around this engine.

## 7.3 Equivalence requirement

Given identical semantic input and configuration, inline and registered execution must produce identical semantic hashes for:

```text
data
document metadata
summary
blocks
chunks
tags
entity tags
reports excluding task-specific operational fields
```

Add equivalence tests for at least:

```text
announcement_doc
event_notice_doc
one general document
one meeting document
one policy document
```

---

# 8. Strict Execution Options and Contract Migration

## 8.1 Objective

Replace uncontrolled public `options: dict[str, Any]` behavior with a versioned strict model.

## 8.2 Required model

Create:

```text
Topic5ExecutionOptions
```

Include only supported Topic 5 execution controls, such as:

```text
mapping_mode
mapping thresholds
strict_metadata_template
strict_output_assertions
enable_llm_fallback
enable_mapping_repair
enable_lineage
strict_lineage
content/package feature toggles
legacy compatibility toggles
```

Do not put Topic 1 scheduling or Topic 6 routing options into it.

## 8.3 Migration

For one compatibility release:

- continue accepting legacy `options`;
- parse known keys into `Topic5ExecutionOptions`;
- reject unknown keys in strict mode;
- emit deprecation warnings;
- detect conflicting values;
- document removal timing.

Do not silently ignore an unknown option.

---

# 9. Deterministic Fingerprints, Replay, and Comparison

## 9.1 Objective

Meet the general governance requirement for reproducible processing and replay without building a global orchestrator.

## 9.2 Conversion fingerprint

Compute:

```text
input_uir_hash
target_schema_hash
metadata_template_hash
mapping_rules_hash
content_organization_hash
execution_options_hash
engine_version
conversion_fingerprint
```

Use canonical JSON serialization:

```text
UTF-8
sorted object keys
stable separators
normalized line endings
no timestamps
no task IDs
```

## 9.3 Semantic artifact hashes

Generate stable hashes for:

```text
structured data
document metadata
document summary
canonical blocks
chunks
tag traces
entity tags
```

Do not include:

```text
task_id
package_id
created_at
runtime duration
absolute paths
```

in semantic hashes.

## 9.4 Replay

Implement a Topic 5-specific replay command:

```text
scripts/replay_topic5_snapshot.py
```

Input:

```text
execution snapshot
or
existing task ID
```

Output:

```text
new execution result
semantic hash comparison
difference report
```

Optional API:

```text
POST /api/v1/topic5/tasks/{task_id}/replay
```

Only implement the API if it can reuse the current task subsystem without becoming a scheduler.

Required acceptance:

```text
same snapshot, same engine version -> identical semantic hashes
changed SchemaPack version -> explicit diff
changed engine version -> explicit diff
```

---

# 10. Package and Filesystem Reliability

## 10.1 Atomic writes

All JSON and text artifact writes must use:

```text
temporary file
fsync where practical
atomic rename
```

Package-directory finalization must be atomic.

## 10.2 Fault injection

Add tests that simulate failure during:

```text
content write
manifest write
verifier execution
ZIP creation
final directory rename
```

Expected:

- no downloadable partial package;
- no stale final package;
- clear error code and stage;
- temporary files cleaned;
- prior valid package preserved.

## 10.3 ZIP safety and reproducibility

Required:

- sorted entries;
- normalized archive paths;
- no absolute paths;
- no `..` traversal;
- deterministic entry metadata where practical;
- ZIP extraction safety test;
- final ZIP hash recorded.

A byte-identical ZIP is optional when operational IDs differ, but the semantic package fingerprint must be identical.

---

# 11. Error Contract and Resource Limits

## 11.1 Structured errors

Introduce:

```python
Topic5Error
```

Required fields:

```text
error_code
stage
path
message
retryable
details
trace_id
```

Stages:

```text
contract
schema_pack
candidate_extraction
mapping
transform
metadata_template
canonical
chunk_provider
content_organization
validation
render
artifact_consistency
package_write
package_verify
replay
```

Do not expose stack traces in public API responses.

## 11.2 Resource limits

Add configurable limits:

```text
max request bytes
max UIR blocks
max block text characters
max assets
max entities
max target fields
max mapping rules
max regex length
max chunks
max output bytes
max ZIP bytes
Topic 11 timeout
```

Reject oversized inputs before expensive processing.

## 11.3 Regex safety

For user-supplied regex:

- limit length;
- reject dangerous unsupported constructs;
- compile at contract-validation time;
- use a timeout-capable engine if available;
- add catastrophic-backtracking fixtures;
- never execute arbitrary expressions.

---

# 12. Performance, Concurrency, and Robustness Evidence

## 12.1 Performance fixtures

Create deterministic fixtures for approximately:

```text
10 blocks
100 blocks
1,000 blocks
10,000 blocks
```

Include:

```text
paragraphs
headings
lists
tables
entities
metadata fields
mapping candidates
```

## 12.2 Metrics

Record:

```text
total duration
candidate extraction duration
mapping duration
transform duration
render duration
chunk duration
verification duration
peak memory
artifact bytes
chunk count
```

Hardware and software environment must be recorded.

Do not use absolute SLO claims without recording hardware.

## 12.3 Concurrency test

Run at least 10 concurrent small/medium conversions through the HTTP API.

Verify:

```text
100% requests reach a terminal status
no cross-task data contamination
unique operational IDs
identical semantic output for identical inputs
no corrupted packages
no shared mutable configuration
```

This is a service reliability test, not a Topic 1 scheduler.

## 12.4 Performance gate

Use regression-based thresholds:

```text
no stage slower by more than 20% versus frozen Batch 2 baseline
no peak-memory increase over 25% without documented reason
no quadratic blow-up between 1,000 and 10,000-block fixtures beyond the declared algorithmic expectation
```

---

# 13. One-Click Downstream Export Verification

## 13.1 Objective

Strengthen the task-book requirement that output can be directly consumed by business ingestion, RAG ingestion, or training-data workflows.

## 13.2 Required exports

From a verified package only:

```text
flat business JSON
CSV for flat Schema fields
RAG JSONL from chunks
training JSONL from chunks and metadata
```

Do not generate question-answer pairs in this batch.

## 13.3 Required behavior

- Exporters read the package contract, not internal database objects.
- Refuse unverified or checksum-invalid packages.
- Preserve source links.
- Preserve entity tags.
- Preserve document and Schema versions.
- Produce deterministic output.
- Explain unsupported nested-to-CSV fields.

## 13.4 Tests

- Announcement package.
- Event notice package.
- Nested/array Schema package.
- Invalid checksum.
- Missing chunk source.
- Unicode.
- Large package.
- Deterministic repeated export.

Acceptance:

```text
verified-package export pass rate = 100%
invalid-package rejection rate = 100%
source-link preservation = 100%
```

---

# 14. Batch 2 Evidence and CI

## 14.1 Evidence directory

Create:

```text
docs/交接/evidence/batch_2/
├── baseline/
├── batch_1_corrections/
├── mapping_v2/
├── runtime_equivalence/
├── replay/
├── package_reliability/
├── performance/
├── downstream/
├── verification/
└── final/
```

## 14.2 Final machine gate

Create:

```text
scripts/check_topic5_batch_2_gate.py
```

It must consume evaluator reports and actual verification outputs.

It must not infer metrics from the fact that a test module passed.

### Mandatory conditions

```text
batch1_proxy_metric_count = 0
raw_verification_log_missing_count = 0
status_truth_table_passed = true
registered_validation_status_regression = 0
package_failure_status_regression = 0
content_json_internal_key_leak_count = 0

tag_gold_frozen = true
content_tag_f1 >= 0.85
management_rule_correctness = 1.0
quality_scope_correctness = 1.0

metadata_effectiveness = 1.0
metadata_localization = 1.0
summary_faithfulness = 1.0
summary_source_coverage = 1.0
summary_new_fact_violations = 0

artifact_consistency_rate = 1.0
package_recomputed_consistency_rate = 1.0
tampering_detection_rate = 1.0
nonempty_canonical_block_chunk_coverage = 1.0
protected_block_integrity = 1.0
invalid_topic11_output_acceptance = 0

invented_entity_id_count = 0
entity_source_coverage = 1.0

auto_exact_field_accuracy >= 0.85
auto_precision >= 0.90
auto_recall >= 0.85
auto_f1 >= 0.87
macro_schema_f1 >= 0.82
required_present_field_recall >= 0.95
mapping_negative_pair_violations = 0
review_required_rate <= 0.20

field_operation_accuracy >= 0.95
schema_localization_rate = 1.0

inline_registered_semantic_equivalence = 1.0
replay_semantic_match_rate = 1.0
partial_package_survival_count = 0
invalid_package_export_acceptance = 0

backend_tests_passed = true
ruff_clean = true
frontend_tests_passed = true
frontend_build_passed = true
openapi_drift = 0
schema_pack_gate_passed = true
github_ci_passed = true
```

If external blind evaluation is unavailable:

```text
external_blind_status = not_run
can_claim_production_blind_0_85 = false
```

This must not fail the public reproducible gate, but the limitation must remain visible.

---

# 15. Required Test Layers

## 15.1 Unit tests

- Strict contracts.
- Feature calculations.
- Constraint solver.
- Calibrator.
- Status evaluator.
- Fingerprinting.
- Error model.
- Resource limits.
- Package finalizer.

## 15.2 Property and fuzz tests

Use Hypothesis or an equivalent local test approach for:

```text
metadata source paths
Schema field structures
transform-rule parameters
regex validation
block identifiers
package paths
chunk source lists
Unicode and empty values
```

## 15.3 Integration tests

- Inline conversion.
- Registered task conversion.
- Inline/registered equivalence.
- Internal chunk provider.
- Topic 11 provider and fallback.
- Package creation and re-verification.
- Replay.
- Exporters.

## 15.4 Negative tests

- Target-ID leakage fixture rejected by benchmark validator.
- Gold changed after freeze.
- Blocked pair selected.
- Invalid cardinality.
- Package content changed with hashes recomputed.
- Ordinary paragraph dropped by Topic 11.
- Internal key leaked into business output.
- Validation fails but task reports completed.
- Package verifier fails but task reports review-required.
- Partial package remains after write failure.
- Unknown execution option silently ignored.

---

# 16. Implementation Order

## Phase A — Corrections

1. Freeze current head and run baseline.
2. Replace proxy metrics.
3. Add executable verification and CI.
4. Fix status semantics.
5. Separate business and operational metadata.
6. Fix package finalization and independent verification.
7. Fix full chunk coverage.
8. Consolidate summary options.
9. Disable legacy transform heuristics by default.
10. Regenerate current status documents.

## Phase B — Benchmark freeze

1. Build mapping v2 dataset and evaluator.
2. Validate leakage rules.
3. Commit dataset and baseline.
4. Record hashes.
5. Do not modify v2 afterward.

## Phase C — Mapping v2

1. Generic descriptors.
2. Configurable feature weights.
3. Constraint graph.
4. True assignment solver.
5. Calibration.
6. Review evidence.
7. Run dev only.
8. Freeze thresholds.
9. Run test.

## Phase D — Runtime convergence

1. Extract pure conversion engine.
2. Use it from both execution paths.
3. Strict execution options.
4. Shared status evaluator.
5. Equivalence tests.

## Phase E — Reproducibility and package reliability

1. Fingerprints.
2. Replay.
3. Atomic package writes.
4. Fault injection.
5. Independent package verifier.

## Phase F — Performance, exports, and final evidence

1. Load fixtures.
2. Concurrency tests.
3. Downstream exports.
4. Full CI.
5. Final gate.
6. Generated documentation.

---

# 17. Suggested Commit Plan

```text
test: capture topic5 batch 2 baseline

fix: replace batch1 proxy metrics with dataset evaluators

ci: add cross-platform topic5 verification workflow

fix: unify conversion status and validation semantics

fix: separate business metadata from operational reports

fix: make package finalization atomic and independently verifiable

fix: require complete canonical block coverage in chunks

refactor: consolidate content organization contract

refactor: move legacy transform heuristics behind compatibility flag

test: freeze topic5 mapping v2 benchmark and baseline

feat: add constrained mapping engine v2

feat: add mapping confidence calibration and review evidence

refactor: unify inline and registered conversion engine

feat: add conversion fingerprints and replay

feat: add resource limits and structured errors

test: add performance concurrency and fault injection evidence

feat: harden verified downstream exports

docs: publish topic5 batch 2 acceptance evidence
```

Do not squash the dataset-freeze commit with mapping-engine changes.

---

# 18. Final Verification Commands

The verification runner must provide one preferred command:

```bash
python scripts/run_topic5_batch_2_verification.py
```

Individual commands should include equivalents of:

```bash
python scripts/eval_topic5_metadata_contract.py
python scripts/eval_topic5_summary_faithfulness.py
python scripts/eval_topic5_artifact_consistency.py
python scripts/eval_topic5_entity_passthrough.py
python scripts/eval_topic5_topic11_adapter.py

python scripts/eval_topic5_mapping_v2.py --split dev
python scripts/eval_topic5_mapping_v2.py --split test
python scripts/check_topic5_mapping_v2_gate.py

python scripts/eval_topic5_field_operations.py
python scripts/eval_topic5_schema_localization.py

python scripts/eval_topic5_runtime_equivalence.py
python scripts/eval_topic5_replay.py
python scripts/eval_topic5_package_faults.py
python scripts/eval_topic5_performance.py
python scripts/eval_downstream_contracts.py

python scripts/check_topic5_batch_2_gate.py
python scripts/verify_all.py --check-openapi
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

Use platform-neutral command construction in Python. Documentation may additionally provide PowerShell examples.

---

# 19. Definition of Done

Batch 2 is complete only when all statements below are true.

1. Batch 1 quantitative metrics come from declared evaluators, not test-pass proxies.
2. Verification logs are non-empty and generated from the current commit.
3. GitHub CI passes on the exact reviewed head.
4. Tag gold is frozen and versioned independently.
5. Inline and registered execution use one conversion engine.
6. Schema validation failure cannot result in `completed`.
7. Any package-verifier failure results in `failed`.
8. `content.json` contains no internal execution snapshot or report leakage.
9. Package verification is independently recomputed from packaged files.
10. No partial package survives a failed build.
11. Every non-empty canonical block is represented in chunks unless explicitly excluded with trace.
12. Topic 11 cannot silently drop ordinary content.
13. Summary configuration has one source of truth.
14. Legacy business-domain transform heuristics are disabled by default.
15. The frozen mapping-v2 test set has no target-ID leakage.
16. Automatic mapping metrics meet the declared Batch 2 thresholds.
17. Review and LLM suggestions are excluded from automatic mapping metrics.
18. Mapping uses a real constrained global assignment solver.
19. Confidence values are calibrated and thresholds are frozen from dev.
20. Same semantic input/configuration produces the same semantic fingerprints.
21. Replay reports exact semantic equivalence or an explicit versioned diff.
22. Resource limits and structured errors are enforced.
23. Verified packages export deterministically to business JSON, CSV, RAG JSONL, and training JSONL.
24. Status and acceptance documents are generated from one machine-readable source.
25. No Topic 1, 2, 3, 4, 6, 7, 10, 11, or 12 core responsibility has been absorbed into Topic 5.

---

# 20. Final Codex Instruction

Proceed with implementation.

Before editing:

1. inspect the current `main` head;
2. confirm or refute every Batch 1 audit finding with file-level evidence;
3. record the baseline;
4. create the Batch 2 branch.

Then implement in the required order.

At completion, return:

```text
audit findings confirmed
audit findings refuted, with evidence
changed files
new contracts
dataset freeze commit
mapping engine commits
commands executed
test results
CI run result
metric results
failed cases
remaining limitations
final commit SHA
```

Do not claim arbitrary-Schema or production-blind mapping performance unless an independent external blind corpus was actually evaluated.

When this specification conflicts with a newer repository state, preserve:

```text
Topic 5 boundary
input/output contract
determinism
traceability
backward compatibility
measured evidence
acceptance thresholds
```

and implement the smallest maintainable correction that satisfies those requirements.
