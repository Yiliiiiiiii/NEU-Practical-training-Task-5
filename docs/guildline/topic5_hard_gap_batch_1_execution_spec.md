# Topic 5 First-Batch Hard-Gap Remediation Execution Specification

**Repository:** `Yiliiiiiiii/NEU-Practical-training-Task-5`  
**Primary branch:** `main`  
**Target system:** Topic 5 — Data Format Standardization Conversion Agent  
**Document purpose:** Direct implementation instructions for Codex  
**Language:** English  
**Execution mode:** Implement, test, document, and produce evidence. Do not stop after writing a plan.

---

## 1. Mission

Close the first batch of hard requirement gaps in the Topic 5 project while strictly preserving the Topic 5 boundary.

The required Topic 5 production contract is:

```text
Normalized UIR
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
    -> field mapping
    -> deterministic field operations
    -> canonical document
    -> machine-readable JSON
    -> human-readable Markdown
    -> chunks with tags, summaries, entities, and source links
    -> validation
    -> manifest/checksums
    -> standard package
```

The task-book requirements that drive this implementation are:

1. A metadata template must be an effective runtime input, not merely stored as unused configuration.
2. Content organization must include content tags, management tags, quality tags, chunk summaries, a document summary, keywords, entity tags, and source backlinks.
3. Human-readable and machine-readable outputs must be consistent and mutually traceable.
4. Field operations and Schema validation must have measurable and reproducible evidence.
5. Topic 5 must expose an integration boundary for Topic 11 chunking, without implementing Topic 11 itself.
6. The service must remain deterministic by default, traceable, replayable, privately deployable, and compatible with existing clients.

---

## 2. Non-Negotiable Topic 5 Boundary

### 2.1 In scope

Implement or improve only the following:

- Metadata-template-driven document metadata.
- Source-to-target field mapping and deterministic field operations.
- Schema validation and exact issue localization.
- Configurable content, management, and quality tags.
- Chunk-level and document-level summaries.
- Upstream entity-tag passthrough.
- JSON, Markdown, and chunk artifact consistency.
- Package assembly, manifest, checksums, and deterministic verification.
- A replaceable Topic 11 chunk-provider interface.
- Tests, fixtures, evaluation scripts, reports, API docs, and reproducibility evidence.

### 2.2 Out of scope

Do not implement any of the following:

- Raw PDF, Word, Excel, image, scan, or OCR parsing.
- Cleaning, de-noising, redaction, or semantic normalization.
- Entity recognition, entity candidate retrieval, entity disambiguation, or entity ID generation.
- Quality scores, quality grades, A/B/C ratings, publication routing, or release decisions.
- LLM-as-Judge or semantic fidelity scoring.
- Vector databases, embeddings, retrieval services, RAG question answering, or Topic 11 research.
- Self-evolution harnesses, automatic gold-set growth, or production model promotion.
- Multi-agent orchestration or a global task scheduler.
- Automatic activation of LLM-generated mapping rules, schemas, templates, or knowledge packs.

### 2.3 Safety rule

LLM output may remain report-only or review-required. It must never directly change production mappings, activate SchemaPacks, write production rules, or bypass deterministic validation.

---

## 3. Current Repository Facts to Preserve

The implementation must preserve the existing architecture and compatibility guarantees:

- Public endpoints:
  - `POST /api/v1/topic5/convert`
  - `POST /api/v1/topic5/convert/package`
- Preferred public mapping field: `mapping_rules`.
- Backward-compatible alias: `mapping_template`.
- Production runtime begins from UIR JSON.
- SchemaPack assets are loaded through `schema_pack.yaml`.
- Existing Package 1.1 consumers and legacy Topic 5 requests must continue to work.
- Existing output assertions remain deterministic SchemaPack-scoped checks.
- Existing review, lineage, evaluation, and LLM components are supporting capabilities, not the main conversion contract.
- Existing tests and reports must not be deleted or weakened merely to make new tests pass.

Known relevant files include:

```text
backend/app/schemas/topic5_convert.py
backend/app/schemas/uir.py
backend/app/schemas/canonical.py
backend/app/schemas/content_organization.py
backend/app/schemas/schema_pack_contract.py

backend/app/services/topic5_conversion_service.py
backend/app/services/task_execution_service.py
backend/app/services/schema_pack_service.py
backend/app/services/canonical_service.py
backend/app/services/render_service.py
backend/app/services/chunk_organizer_service.py
backend/app/services/package_service.py
backend/app/services/package_verifier_service.py
backend/app/services/validation_service.py
backend/app/services/transform_service.py

schema_packs/examples/*/schema_pack.yaml
schema_packs/examples/*/metadata_template.json
schema_packs/examples/*/content_org.yaml

backend/tests/
scripts/
docs/
reports/
```

Suggested file paths in this document are implementation guidance. Inspect the current repository before editing and adapt paths only when the repository has evolved.

---

## 4. Codex Operating Instructions

### 4.1 Start from a clean, inspectable branch

Create a dedicated branch:

```text
feat/topic5-hard-gap-batch-1
```

Do not commit unrelated workspace changes.

### 4.2 Record the baseline before modifying code

Run and save the output of:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

Push-Location frontend
npm.cmd test
Pop-Location
```

Also run the relevant current Topic 5, package, SchemaPack, content-organization, and field-operation tests independently.

Create:

```text
docs/交接/evidence/hard_gap_batch_1/baseline/
```

Store:

- Git commit SHA.
- Python version.
- Node version.
- Backend test summary.
- Ruff summary.
- Frontend test summary.
- OpenAPI path count.
- Existing mapping and package gate summaries.
- A list of any pre-existing failures.

Do not silently fix unrelated baseline failures. Record them separately.

### 4.3 Implementation discipline

For each workstream:

1. Add or update strict Pydantic models first.
2. Add unit tests for the model and service.
3. Implement the service.
4. Integrate it into both inline conversion and registered task execution.
5. Add package/API integration tests.
6. Add negative and backward-compatibility tests.
7. Update documentation and examples.
8. Run the full verification suite.
9. Commit the workstream separately.

### 4.4 No benchmark shortcut

Do not make a metric pass by:

- Placing target field IDs directly in evaluation input unless the test explicitly measures exact-name mapping.
- Copying gold labels into runtime configuration.
- Adding document-ID-specific rules.
- Editing expected outputs to match incorrect behavior.
- Globally tagging all chunks to maximize recall.
- Treating review-required support as automatic mapping.
- Counting package parseability as semantic or cross-artifact consistency.

---

# 5. Workstream A — Make Metadata Templates Effective

## 5.1 Objective

Make `metadata_template` deterministically control document-level metadata in:

- Inline API responses.
- Registered SchemaPack task execution.
- `content.json`.
- `metadata.json`.
- The canonical model.
- Trace and validation reports.

The same UIR with different valid metadata templates must produce different, valid document metadata without changing backend code.

## 5.2 Current problem

The request accepts a metadata template, but the conversion path currently stores it in options and does not prove that it controls output metadata. Existing package metadata is primarily technical package information.

## 5.3 Required design

Create strict metadata-template schemas in a dedicated module, for example:

```text
backend/app/schemas/metadata_template.py
```

Recommended models:

```text
MetadataValueSource
MetadataFieldConfig
MetadataTemplateConfig
MetadataFieldTrace
MetadataTemplateIssue
MetadataTemplateReport
MetadataRenderResult
```

### 5.3.1 Required field model

Support at least:

```text
field_id
type
required
source_path
default
allow_empty
description
```

Recommended allowed types:

```text
any
string
integer
number
boolean
array
object
date
datetime
```

Existing templates containing only:

```json
{
  "field_id": "language",
  "required": false,
  "default": "zh-CN"
}
```

must remain valid.

### 5.3.2 Deterministic source resolution

Use this order when `source_path` is omitted:

1. `uir.metadata.<field_id>`
2. `transform_result.data.<field_id>`
3. configured default
4. missing

Allow explicit safe paths only under whitelisted roots:

```text
uir.metadata.*
transformed_fields.*
system.*
```

Do not implement arbitrary JSONPath, Python expressions, template evaluation, or executable rules.

Whitelisted `system` values may include:

```text
doc_id
schema_id
schema_version
template_id
template_version
metadata_template_id
metadata_template_version
```

Do not use non-deterministic timestamps as semantic document metadata unless explicitly requested by a system field and clearly marked as operational metadata.

### 5.3.3 Metadata output structure

Keep technical package metadata separate from document metadata.

For backward compatibility, preserve existing top-level technical keys in `metadata.json`, then add:

```json
{
  "document_metadata": {},
  "metadata_template": {
    "template_id": "...",
    "schema_id": "...",
    "version": "..."
  },
  "metadata_field_trace": [],
  "features": [
    "metadata_template_v1"
  ]
}
```

Add to `content.json`:

```json
{
  "document_metadata": {},
  "metadata_template": {
    "template_id": "...",
    "version": "..."
  }
}
```

The legacy `metadata` field may remain for compatibility, but its behavior must be documented. Do not continue merging internal execution snapshots, mapping summaries, and source metadata into one ambiguous object without an explicit compatibility reason.

### 5.3.4 Canonical integration

Add document metadata to `CanonicalModel.doc_meta` under explicit keys:

```text
source_metadata
document_metadata
metadata_template
metadata_template_report
execution_snapshot
```

Do not place all internal dictionaries under a single overloaded `metadata` object.

### 5.3.5 Validation behavior

A missing required metadata field must:

- Produce a field-specific issue.
- Include the exact metadata field path.
- Mark the conversion as `review_required` by default.
- Become `failed` only if a new explicit strict metadata option is enabled.
- Never be silently replaced by `null`.

A type mismatch must report:

```text
stage = metadata_template
path = document_metadata.<field_id>
error_code = metadata_type_mismatch
```

### 5.3.6 Suggested service

Create:

```text
backend/app/services/metadata_template_service.py
```

Recommended interface:

```python
render(
    *,
    uir: UIRDocument,
    transformed_fields: dict[str, Any],
    template: MetadataTemplateConfig,
    system_context: dict[str, Any],
) -> MetadataRenderResult
```

The result must contain:

- Resolved metadata.
- Per-field source trace.
- Defaults used.
- Missing required fields.
- Type errors.
- Overall `passed` boolean.
- No quality score or quality grade.

## 5.4 Pipeline integration

Integrate into both:

```text
Topic5ConversionService.convert
TaskExecutionService._execute
```

Recommended order:

```text
Transform
-> MetadataTemplateService.render
-> CanonicalService.build_canonical
-> Render
-> Content Organization
-> Validation
-> Consistency Validation
-> Package
```

Registered SchemaPack execution must load and validate `metadata_template` through `SchemaPackService`, not only inline execution.

## 5.5 Required tests

Add at least:

1. Existing simple metadata templates remain valid.
2. Same-name value resolves from UIR metadata.
3. Same-name value falls back to transformed fields.
4. Explicit `source_path` works.
5. Default value is used and traced.
6. Required missing field is localized.
7. Wrong type is localized.
8. Unknown source root is rejected.
9. Path traversal or expression-like path is rejected.
10. Two templates applied to one UIR produce different document metadata.
11. Inline API and registered SchemaPack execution produce equivalent metadata.
12. Metadata appears in content JSON and package metadata.
13. Legacy requests without metadata template retain documented behavior.
14. Package verifier detects a declared metadata report that is missing or invalid.

## 5.6 Acceptance criteria

- Metadata template is consumed in both execution paths.
- Required missing localization rate: `100%`.
- Type error localization rate: `100%`.
- Template-driven output difference test passes.
- No arbitrary expression execution.
- Existing SchemaPack examples still validate.
- No existing public request becomes invalid solely because it omitted new optional fields.

---

# 6. Workstream B — Move Three-Level Tag Rules into SchemaPack Configuration

## 6.1 Objective

Remove document-family-specific tag logic from backend code and make new SchemaPacks configurable without code changes.

The three tag levels are:

```text
content tags
management tags
quality tags
```

## 6.2 Current problem

Content rules are currently associated with hard-coded schema IDs, while management and quality tags mix operational identifiers, global document state, and chunk-local quality state. This causes low precision and makes new SchemaPacks depend on backend edits.

## 6.3 Required configuration design

Extend the existing `content_org.yaml` contract rather than adding executable scripts.

Recommended structure:

```yaml
chunk_strategy: source_block_aware
target_tokens: 768
min_tokens: 128
max_tokens: 1024
overlap_tokens: 80

summary:
  chunk_mode: deterministic
  document_mode: extractive
  document_max_sentences: 5
  document_max_chars: 500

tag_rules:
  content:
    base_tags:
      - announcement
    rules:
      - tag: maintenance
        any_terms:
          - maintenance
          - system upgrade
        title_terms: []
        block_types: []

  management:
    static_tags:
      - domain:campus
    metadata_rules:
      - tag_template: "language:{value}"
        source_path: document_metadata.language
        omit_if_missing: true

  quality:
    enabled_builtin_rules:
      - source_linked
      - anchor_linked
      - empty_text
      - short_chunk
      - overlong_chunk
      - summary_missing
      - keyword_missing
      - mapping_review_required
      - validation_error
```

Use strict models. Reject unknown operators and invalid tag templates.

## 6.4 Allowed deterministic rule operators

Support only a limited, auditable set:

### Content rules

- `any_terms`
- `all_terms`
- `none_terms`
- `title_terms`
- `block_types`
- optional case sensitivity

### Management rules

- static tags
- value from `document_metadata`
- value from whitelisted package/schema metadata
- omission when missing
- deterministic string formatting with one `{value}` placeholder

### Quality rules

Quality tags must be generated from engine facts, not arbitrary text scripts. A SchemaPack may enable or disable supported built-in local rules, but must not execute custom code.

## 6.5 Migration

Move all current document-family-specific tag terms into the corresponding example SchemaPacks.

At minimum, migrate rules for the existing families that currently depend on backend constants, including:

```text
policy_doc
contract_doc
meeting_doc
general_doc
announcement_doc
event_notice_doc
procurement_doc
```

After migration:

- Remove the hard-coded schema-family rule dictionary from `ChunkOrganizerService`.
- A new SchemaPack with its own content rules must work without a backend edit.
- A SchemaPack with no content rules must receive only a deterministic generic base tag, such as the normalized schema ID, and no fabricated domain-specific tags.

## 6.6 Operational metadata separation

Do not count the following as management tags:

```text
task_id
doc_id
chunk_index
```

Keep them as explicit chunk fields or operational metadata.

Management tags should represent governance and business metadata, for example:

```text
domain
language
source
department
classification
lifecycle
retention policy
review status
```

Only generate them when backed by configuration or document metadata.

## 6.7 Required tests

1. Existing migrated SchemaPacks reproduce intended content tags.
2. New temporary SchemaPack generates tags without code changes.
3. Unknown tag-rule operator is rejected.
4. Management tags use document metadata.
5. Missing optional management metadata omits the tag.
6. Operational identifiers remain fields and are not included in management tags.
7. No document-family-specific tag dictionary remains in the service.
8. Tag generation is deterministic across repeated runs.
9. Empty rule configuration is valid.
10. Malformed tag templates are rejected.

## 6.8 Acceptance criteria

- No backend source code contains a schema-ID-to-domain-tag rule table.
- New SchemaPack tag behavior is configuration-only.
- Content-tag evaluation meets or exceeds `0.85` accuracy/F1 on the declared evaluation set.
- Management-tag rule correctness is `100%` on deterministic fixtures.
- Unknown tag count is zero for the declared examples.
- All generated tags have trace entries identifying rule ID and source.

---

# 7. Workstream C — Fix Chunk-Local Quality Tags

## 7.1 Objective

Prevent one document-level mapping or validation problem from contaminating every chunk.

## 7.2 Required behavior

Generate `mapping_review_required` only when the review item is relevant to that chunk.

A review item is relevant when at least one of the following is true:

- Its `source_blocks` intersect the chunk `source_block_ids`.
- Its source path resolves to a block used by the chunk.
- Its target field maps to canonical field source blocks used by the chunk.

Generate `validation_error` only when:

- The validation issue points to a field whose canonical source blocks intersect the chunk.
- The issue points directly to the chunk or its source block.
- The issue is a chunk-specific organization issue.

Global issues that cannot be localized must appear in:

```text
ContentOrganizationReport.document_quality_flags
```

They must not be copied to every chunk.

## 7.3 Required quality-tag categories

### Chunk-local positive facts

```text
source_linked
anchor_linked
length_ok
summarized
keyworded
entity_linked
```

### Chunk-local warnings/errors

```text
empty_text
short_chunk
overlong_chunk
oversized_protected_block
summary_missing
keyword_missing
source_unlinked
mapping_review_required
validation_error
entity_unlinked
```

Do not create a quality score or quality grade.

## 7.4 Required trace

For each generated quality tag, retain:

```text
tag
rule_id
scope = chunk
evidence
source_block_ids
related_field_ids
related_issue_codes
```

Document-level flags must use:

```text
scope = document
```

## 7.5 Required tests

1. One review item associated with block A tags only chunk A.
2. Chunk B in the same document does not receive that tag.
3. One field validation error tags only chunks linked to that field.
4. Unlocalizable issue appears only in document-level flags.
5. Empty chunk receives local empty-text tags.
6. Long protected table receives the expected local warning.
7. Tag precision regression fixture.
8. Repeated execution produces identical tags and traces.

## 7.6 Acceptance criteria

- No global broadcast of mapping-review tags.
- No global broadcast of field validation errors.
- Quality-tag precision materially improves from the prior baseline.
- Target evaluation: quality-tag F1 at least `0.85`.
- All chunk-local quality tags have evidence and scope.

---

# 8. Workstream D — Add a Faithful Document-Level Summary

## 8.1 Objective

Produce both:

- Chunk-level summaries.
- A document-level summary.

The first-batch document summary must be deterministic and extractive.

## 8.2 Boundary

Do not add LLM-generated abstractive summarization in this batch.

The summary must not introduce:

- New dates.
- New amounts.
- New organizations.
- New obligations.
- New conclusions.
- New facts not present in source blocks.

## 8.3 Required data model

Create a model such as:

```python
DocumentSummary
```

Recommended fields:

```text
text
mode
source_block_ids
source_chunk_ids
sentence_traces
char_count
generated_by
faithfulness_passed
warnings
```

Each sentence trace must include:

```text
summary_sentence
source_block_id
source_text_span
```

## 8.4 Deterministic algorithm

Recommended extractive baseline:

1. Use the canonical title field or first heading only as context, not as a fabricated sentence.
2. Traverse top-level sections in source order.
3. Select the first meaningful source sentence from each section.
4. Deduplicate normalized sentences.
5. Respect:
   - `document_max_sentences`
   - `document_max_chars`
6. Preserve exact source wording except normalized whitespace.
7. If no section structure exists, select the first meaningful sentences in source order.
8. If the document is empty, return an empty summary plus a warning.

## 8.5 Configuration

Extend content organization configuration with strict fields such as:

```text
chunk_summary_mode
document_summary_mode
document_summary_max_sentences
document_summary_max_chars
```

Recommended modes:

```text
none
deterministic
extractive
```

For this batch, `extractive` and `deterministic` may use the same safe implementation if documented.

## 8.6 Output placement

Add the document summary to:

- `content.json`.
- `Topic5ConvertResponse`.
- `content_organization_report`.
- `metadata.json` as a reference or embedded summary.
- Markdown under a clearly marked `Document Summary` section when enabled.

Do not create contradictory copies. Use one `DocumentSummary` object as the source for all renderers.

## 8.7 Faithfulness checks

Before packaging:

- Every summary sentence must map to a source block.
- Every sentence must be an exact or whitespace-normalized source substring.
- No new date-like token may appear.
- No new amount-like token may appear.
- No new organization token may appear when the token is absent from source.
- The summary must satisfy configured length limits.

A failure must produce `review_required`, not a quality score.

## 8.8 Required tests

1. Multi-section document summary.
2. No-heading fallback.
3. Duplicate sentence removal.
4. Maximum sentence limit.
5. Maximum character limit.
6. Empty document.
7. Table-only document.
8. No new date.
9. No new amount.
10. No new organization.
11. Sentence trace exactness.
12. Same input/config produces identical summary.
13. Summary disabled mode.
14. Markdown and JSON contain the same summary object/text.

## 8.9 Acceptance criteria

- Document summary is present when enabled.
- Faithfulness pass rate is `100%` on deterministic extractive fixtures.
- Source trace coverage is `100%`.
- No new date, amount, or organization violations.
- No overlong summary in the acceptance fixture set.

---

# 9. Workstream E — Implement Deterministic JSON–Markdown–Chunk Consistency Validation

## 9.1 Objective

Prove that human-readable and machine-readable artifacts represent the same canonical result.

Package parseability, checksums, and non-empty Markdown are not enough.

## 9.2 Single-source rule

`CanonicalModel` must remain the only semantic source for:

```text
content.json
content.md
chunks.jsonl
document metadata
document summary
```

No renderer may independently reconstruct semantic values from unrelated inputs.

## 9.3 Markdown contract

Add deterministic machine-readable markers without harming human readability.

Recommended structure:

````markdown
<!-- topic5:document:start doc_id="..." schema_id="..." -->

# Document Title

## Document Summary

...

## Structured Data

<!-- topic5:structured-data:start -->
```json
{
  "data": {},
  "document_metadata": {}
}
```
<!-- topic5:structured-data:end -->

## Content

<!-- topic5:block:start id="block_1" hash="sha256:..." -->
...
<!-- topic5:block:end id="block_1" -->

<!-- topic5:document:end -->
````

Requirements:

- Escape Markdown safely.
- Preserve table, list, and code-block semantics.
- Every canonical block must have one stable Markdown anchor.
- Every Markdown block marker must refer to a real canonical block.
- The embedded structured data must be generated from the same object used for `content.json`.

## 9.4 Consistency service

Create:

```text
backend/app/services/artifact_consistency_service.py
```

Recommended input:

```python
verify(
    *,
    canonical: CanonicalModel,
    structured_json: dict[str, Any],
    markdown: str,
    chunks: list[dict[str, Any]],
    document_summary: DocumentSummary | None,
) -> ArtifactConsistencyReport
```

Required checks:

### JSON checks

- Every canonical field equals `content.json.data[field_id]`.
- No expected field is missing.
- Document metadata equals the metadata-template result.
- Document summary equals the shared summary object.

### Markdown checks

- Embedded structured data parses.
- Embedded data equals JSON data and document metadata.
- Every canonical block has exactly one marker.
- No unknown block marker exists.
- Block order equals canonical order.
- Block hashes match.
- Document summary text equals JSON summary text.

### Chunk checks

- Every source block ID exists.
- Every source link refers to the correct block.
- Chunk text is derivable from its declared source blocks.
- Entity tags only refer to entities relevant to the chunk.
- Parent chunk IDs, when present, exist.
- Chunk indices are unique and deterministic.

### Cross-artifact checks

- `doc_id`, `schema_id`, and template versions agree.
- Summary, metadata, and data values agree.
- No duplicate or conflicting canonical identifiers.
- Every artifact has traceability to the canonical model.

## 9.5 Report model

Create:

```python
ArtifactConsistencyReport
ArtifactConsistencyIssue
```

Required fields:

```text
passed
checks
errors
warnings
field_coverage
block_coverage
chunk_source_coverage
summary_consistent
metadata_consistent
```

Do not include a quality score or grade.

## 9.6 Package integration

New packages must include:

```text
artifact_consistency_report.json
metadata_template_report.json
```

Add corresponding manifest roles and hashes.

For backward compatibility:

- Old packages without the new feature declaration may still be read using the legacy verifier profile.
- New packages must declare features in `metadata.json`, for example:

```json
{
  "features": [
    "metadata_template_v1",
    "artifact_consistency_v1",
    "document_summary_v1"
  ]
}
```

- When `artifact_consistency_v1` is declared, the report is required and must pass.
- Package creation must fail or return `review_required` according to the existing status contract when consistency fails.
- Do not claim consistency based only on a precomputed report. The package verifier must at least validate that the report exists, parses, is manifested, has a valid checksum, and declares `passed=true`.

## 9.7 Required negative tests

1. JSON field value changed after render.
2. Markdown embedded data changed.
3. Markdown block omitted.
4. Unknown Markdown block marker added.
5. Block order changed.
6. Chunk references unknown source block.
7. Chunk text not derived from declared source.
8. Summary differs between JSON and Markdown.
9. Document metadata differs between JSON and package metadata.
10. Consistency report missing while feature declared.
11. Consistency report checksum mismatch.
12. Legacy package without feature remains readable.

## 9.8 Acceptance criteria

- New package consistency rate: `100%`.
- Human/machine semantic field consistency: `100%`.
- Canonical block Markdown coverage: `100%`.
- Chunk source-link coverage: `100%`.
- All negative tampering fixtures are detected.
- Legacy package compatibility remains tested.

---

# 10. Workstream F — Replace Entity Guessing with Upstream Entity Passthrough

## 10.1 Objective

Topic 5 must write standard entity tags into chunks without performing entity linking or inventing standard IDs.

## 10.2 UIR contract extension

Add an optional, backward-compatible entity model to UIR.

Recommended model:

```python
UIREntity
```

Recommended fields:

```text
mention
canonical_name
entity_type
normalized_id
link_status
confidence
source_block_ids
source_agent
evidence
```

Recommended `link_status` values:

```text
linked
unlinked
nil
```

Add to `UIRDocument`:

```python
entities: list[UIREntity] = Field(default_factory=list)
```

Backward compatibility is mandatory.

Optionally support legacy block-level entity data through an adapter, but normalize it into `UIREntity` before chunk organization.

## 10.3 Strict boundary behavior

Topic 5 may:

- Validate upstream entity objects.
- Copy them into canonical metadata.
- Attach them to relevant chunks.
- Preserve source block IDs and standard IDs.
- Mark an entity as unlinked or NIL when upstream says so.

Topic 5 must not:

- Search an entity knowledge base.
- Generate candidate entities.
- Disambiguate same-name entities.
- Create a normalized ID.
- Upgrade an unlinked mention to linked.
- Guess entity type from field names by default.

Remove or disable the existing default heuristic that infers entity status from field names such as company, organization, person, department, party, and similar hints.

If temporary compatibility is necessary, keep legacy inference behind an explicit disabled-by-default option:

```text
enable_legacy_entity_inference = false
```

Do not use it in acceptance evidence.

## 10.4 Chunk assignment

Attach an entity to a chunk when:

- Entity `source_block_ids` intersect chunk source blocks; or
- A legacy entity lacks block IDs and the exact mention is present in chunk text.

The first method has priority.

Entity output must preserve:

```text
mention
canonical_name
entity_type
normalized_id
link_status
confidence
source_block_ids
source_agent
```

Do not replace a missing normalized ID with a synthetic value.

## 10.5 Required tests

1. Linked upstream entity is copied with the same ID.
2. Unlinked entity remains unlinked.
3. NIL entity remains NIL.
4. No entity ID is invented.
5. Entity appears only in relevant chunks.
6. Entity with multiple source blocks appears in all relevant chunks.
7. Unknown source block is rejected or reported.
8. Legacy UIR without `entities` still converts.
9. Legacy inference is disabled by default.
10. Exact repeated runs are deterministic.

## 10.6 Acceptance criteria

- Standard entity passthrough coverage: `100%` on fixtures.
- Invented normalized entity IDs: `0`.
- Entity-linking calls: `0`.
- Chunk/entity source-block trace coverage: `100%`.

---

# 11. Workstream G — Add a Replaceable Topic 11 Chunk Provider Interface

## 11.1 Objective

Provide the required integration boundary for Topic 11 while keeping the current internal deterministic chunker as the default.

## 11.2 Architecture

Create an interface such as:

```text
ChunkProvider
├── InternalDeterministicChunkProvider
├── Topic11HttpChunkProvider
└── ChunkProviderResolver / FallbackChunkProvider
```

Suggested files:

```text
backend/app/services/chunk_providers/base.py
backend/app/services/chunk_providers/internal.py
backend/app/services/chunk_providers/topic11_http.py
backend/app/services/chunk_providers/resolver.py
backend/app/schemas/chunk_provider.py
```

## 11.3 Provider contract

Recommended request:

```json
{
  "contract_version": "1.0",
  "doc_id": "...",
  "schema_id": "...",
  "blocks": [],
  "entities": [],
  "document_metadata": {},
  "chunk_config": {}
}
```

Recommended response:

```json
{
  "contract_version": "1.0",
  "provider": "topic11",
  "provider_version": "...",
  "chunks": [],
  "warnings": [],
  "trace": {}
}
```

Add JSON Schema files under:

```text
contracts/
```

Document the contract.

## 11.4 Runtime configuration

Use environment/runtime settings for network configuration:

```text
TOPIC11_BASE_URL
TOPIC11_TIMEOUT_SECONDS
TOPIC11_API_KEY
```

Do not store live endpoints or secrets in SchemaPack examples.

Content organization configuration may select:

```text
provider = internal
provider = topic11
```

Default:

```text
internal
```

Recommended options:

```text
fallback_to_internal
strict_provider
```

## 11.5 External output validation

Before accepting Topic 11 output:

- Validate response schema.
- Verify all source block IDs exist.
- Verify every chunk has text.
- Verify chunk text is derivable from declared source blocks.
- Verify source links are complete.
- Verify protected tables/code blocks were not silently dropped.
- Reject unknown entity IDs.
- Reject duplicate chunk IDs.
- Do not accept generated facts or text absent from source blocks.

If validation fails:

- Fallback to internal provider when configured.
- Record the exact fallback reason.
- Never silently accept invalid external chunks.

## 11.6 Provider trace

Add to `ContentOrganizationReport`:

```text
requested_provider
used_provider
provider_version
external_requested
external_used
fallback_used
fallback_reason
latency_ms
validation_passed
```

No retrieval score or Topic 11 research metric is required in Topic 5.

## 11.7 Required tests

Use mocks only; no live network dependency.

1. Internal provider default.
2. Topic 11 valid response.
3. Timeout with fallback.
4. HTTP error with fallback.
5. Invalid schema with fallback.
6. Unknown source block rejection.
7. Hallucinated chunk text rejection.
8. Strict provider mode returns failure.
9. Missing endpoint configuration produces clear error/fallback.
10. Secret is not written into logs, reports, snapshots, or packages.
11. Offline execution remains fully functional.
12. Inline and registered task execution use the same resolver.

## 11.8 Acceptance criteria

- Internal mode works with no network.
- Topic 11 adapter is replaceable and contract-driven.
- Fallback test success rate: `100%`.
- Invalid external output acceptance rate: `0%`.
- Secret leakage: `0`.
- No vector store, embedding model, retrieval system, or RAG QA implementation is added.

---

# 12. Workstream H — Expand Field Operation and Schema Localization Evidence

## 12.1 Objective

Replace tiny demonstration samples with credible dataset-driven evidence.

## 12.2 Field operation fixture requirements

Create a versioned fixture set, for example:

```text
eval/topic5_field_operations/
```

Minimum recommended distribution:

| Operation | Minimum cases |
|---|---:|
| Rename | 20 |
| Merge | 15 |
| Split | 15 |
| Type/format conversion | 20 |
| Default/missing handling | 10 |
| Nested/array operations | 10 |
| Negative/unsafe operations | 20 |

Total target: at least `110` cases.

Required coverage:

- Chinese and English field names.
- Empty string versus null.
- Multiple source fields merged in order.
- One source field split by Chinese and English separators.
- Arrays and nested objects.
- Date and datetime formats.
- Numeric precision.
- Boolean conversion.
- Enum validation.
- Unsupported conversion.
- Unsafe implicit coercion.
- Long text.
- Duplicate source candidate.
- Missing source field.
- Required target field.
- Blocked semantic pairs.

## 12.3 Schema validation localization fixture requirements

Create at least `40` cases covering:

- Missing required field.
- Wrong scalar type.
- Wrong array element type.
- Wrong nested object path.
- Invalid date/datetime.
- Invalid enum.
- Min/max violation.
- Pattern mismatch.
- Unexpected field when forbidden.
- Invalid metadata field.
- Invalid chunk source link.
- Invalid package artifact role.
- Missing consistency report under declared feature.
- Invalid entity source block.

Each expected issue must define:

```text
expected_error_code
expected_path
expected_stage
```

Localization is correct only when all three match.

## 12.4 Evaluation scripts

Add scripts such as:

```text
scripts/eval_topic5_field_operations.py
scripts/eval_topic5_schema_localization.py
scripts/check_topic5_hard_gap_batch_1_gate.py
```

Required metrics:

```text
field_operation_accuracy
rename_accuracy
merge_accuracy
split_accuracy
conversion_accuracy
unsafe_operation_count
schema_localization_rate
error_code_accuracy
stage_accuracy
```

Keep metrics deterministic.

## 12.5 Gate thresholds

Minimum acceptance:

```text
field_operation_accuracy >= 0.95
rename_accuracy >= 0.95
merge_accuracy >= 0.95
split_accuracy >= 0.95
unsafe_operation_count = 0
schema_localization_rate = 1.00
error_code_accuracy = 1.00
stage_accuracy = 1.00
```

Do not reduce the denominator by excluding failed or difficult cases.

## 12.6 Required reports

Generate JSON and Markdown reports under:

```text
docs/交接/evidence/hard_gap_batch_1/operations/
```

Include:

- Commit SHA.
- Dataset hash.
- Case counts.
- Per-operation metrics.
- Failed case list.
- Reproduction command.
- Claim boundary.

---

# 13. Cross-Cutting API and Schema Changes

## 13.1 Suggested response additions

Add backward-compatible optional response fields:

```text
document_metadata
metadata_template_report
document_summary
artifact_consistency_report
```

Do not remove or rename existing response fields.

## 13.2 Suggested report additions

Extend `ContentOrganizationReport` with:

```text
document_summary
document_quality_flags
provider_trace
tag_rule_summary
```

## 13.3 Strict configuration

Replace untyped nested dictionaries introduced by this batch with strict Pydantic models.

All new models must:

- Reject unknown fields unless backward compatibility explicitly requires otherwise.
- Validate token and length limits.
- Validate source paths.
- Validate tag rule operators.
- Validate provider selection.
- Validate entity status.
- Validate feature declarations.

## 13.4 OpenAPI

Regenerate:

```text
docs/openapi.json
```

Update:

```text
docs/topic5_convert_api.md
docs/schema_pack_contract.md
docs/package_spec.md
docs/lineage.md
schema_packs/README.md
```

Document new fields and legacy behavior.

---

# 14. Package and Manifest Requirements

Newly generated packages must contain at least:

```text
content.json
content.md
chunks.jsonl
metadata.json
mapping_report.json
transform_report.json
validation_report.json
content_organization_report.json
metadata_template_report.json
artifact_consistency_report.json
canonical.json
manifest.json
verifier_report.json
standard_package.zip
```

Requirements:

- All files except the ZIP itself are included in the manifest as appropriate.
- All manifested hashes are correct.
- New report roles are registered.
- Feature declarations determine which additive reports are mandatory.
- Legacy packages remain readable.
- New packages fail verification when a declared mandatory artifact is missing.
- Package verification still does not claim semantic quality scoring.

---

# 15. Lineage Requirements

Extend lineage only as needed for Topic 5 outputs.

Required additional edges:

```text
metadata field -> source UIR metadata/transformed field/default
document summary sentence -> source block
content tag -> rule ID + chunk
management tag -> metadata field/rule ID + chunk
quality tag -> local issue/rule ID + chunk
entity tag -> upstream entity + source block + chunk
Markdown block -> canonical block
content.json field -> canonical field
chunk -> canonical/source blocks
```

Do not build cross-agent orchestration lineage.

Required coverage for acceptance fixtures:

```text
metadata source coverage = 100%
summary source coverage = 100%
tag trace coverage = 100%
entity source coverage = 100%
Markdown block coverage = 100%
chunk source coverage = 100%
```

---

# 16. Implementation Order and Dependencies

Use this order:

## Phase 0 — Baseline and contracts

- Baseline verification.
- Add strict models.
- Freeze new JSON Schema contracts.
- Add feature declarations.

## Phase 1 — Metadata engine

- Metadata template service.
- Canonical integration.
- Inline and registered execution integration.
- Package output and report.

## Phase 2 — Tag rules and local quality scope

- Move hard-coded content rules to SchemaPacks.
- Implement management tag rules.
- Implement local quality indexing.
- Add document-level quality flags.

## Phase 3 — Entity passthrough and summaries

- Add optional UIR entity contract.
- Remove default heuristic entity guessing.
- Add deterministic document summary and traces.

## Phase 4 — Chunk provider interface

- Extract internal provider.
- Add Topic 11 HTTP adapter.
- Add validation and fallback.
- Add provider trace.

## Phase 5 — Artifact consistency

- Update Markdown contract.
- Add consistency service.
- Add package feature checks.
- Add tampering tests.

## Phase 6 — Evidence expansion

- Large operation fixture.
- Schema localization fixture.
- Evaluation scripts.
- Hard-gap gate.
- Documentation synchronization.

Do not implement artifact consistency before the canonical metadata and document summary structures are stable.

---

# 17. Required Test Layers

## 17.1 Unit tests

Test every new strict model and pure service independently.

## 17.2 Service integration tests

Cover:

- Inline conversion.
- Registered SchemaPack conversion.
- Package creation.
- Package verification.
- Legacy requests.
- Legacy packages.
- Feature-declared packages.

## 17.3 API tests

Cover:

- Valid request.
- Invalid metadata template.
- Invalid content organization rules.
- Topic 11 selection with missing endpoint.
- New response fields.
- Status behavior.
- 422 validation behavior.

## 17.4 Golden package tests

Add at least two new golden packages:

```text
announcement_doc
event_notice_doc
```

Each must prove:

- Metadata template effect.
- Configured tags.
- Chunk-local quality tags.
- Document summary.
- Entity passthrough.
- Markdown anchors.
- Artifact consistency.
- Manifest/checksum validity.

## 17.5 Mutation/tampering tests

Mutate one artifact at a time and prove detection.

## 17.6 Determinism test

Run the same input and configuration at least three times.

Compare semantic artifact hashes after excluding explicitly operational values such as task ID and creation time.

Expected:

```text
content semantic hash: identical
document metadata hash: identical
summary hash: identical
chunk semantic hashes: identical
tag traces: identical
entity tags: identical
consistency checks: identical
```

---

# 18. Hard-Gap Batch 1 Acceptance Gate

Create:

```text
scripts/check_topic5_hard_gap_batch_1_gate.py
```

The gate must fail if any required condition is not met.

Required conditions:

```text
metadata_template_effective = true
metadata_required_localization_rate = 1.0

content_tag_metric >= 0.85
management_tag_rule_accuracy = 1.0
quality_tag_metric >= 0.85
global_quality_tag_pollution_count = 0

document_summary_faithfulness = 1.0
document_summary_source_coverage = 1.0
document_summary_new_fact_violations = 0

artifact_consistency_pass_rate = 1.0
markdown_block_coverage = 1.0
chunk_source_coverage = 1.0
tampering_detection_rate = 1.0

entity_passthrough_coverage = 1.0
invented_entity_id_count = 0

topic11_invalid_output_acceptance_count = 0
topic11_fallback_success_rate = 1.0
secret_leak_count = 0

field_operation_accuracy >= 0.95
schema_localization_rate = 1.0

legacy_request_regression = 0
legacy_package_regression = 0
full_backend_tests_passed = true
ruff_clean = true
frontend_tests_passed = true
openapi_export_passed = true
```

The gate must output:

```text
JSON report
Markdown report
machine-readable exit code
```

Final conclusion values:

```text
passed
failed
```

Do not use quality grades or publication routing.

---

# 19. Documentation Deliverables

Update or add:

```text
docs/topic5_convert_api.md
docs/schema_pack_contract.md
docs/package_spec.md
docs/lineage.md
docs/交接/project_status.md
docs/交接/requirement_mapping.md
docs/交接/acceptance_report.md
docs/交接/验证与复现.md
docs/交接/已知边界与后续事项.md
```

Add a dedicated implementation result:

```text
docs/交接/topic5_hard_gap_batch_1_result.md
```

It must include:

- What changed.
- Why each change belongs to Topic 5.
- What was deliberately not implemented.
- Exact input/output examples.
- Migration notes.
- Metrics.
- Failed cases, if any.
- Reproduction commands.
- Commit SHA.
- Dataset hashes.
- Claim boundary.

Avoid manually copying metrics into many files without a source. Prefer generating shared metric sections from one final JSON report.

---

# 20. Suggested Commit Plan

Use focused commits:

```text
test: capture topic5 hard-gap batch 1 baseline

feat: implement metadata template rendering and trace

feat: move topic5 tag rules into schemapack config

fix: localize chunk quality tags and document flags

feat: add upstream entity passthrough

feat: add deterministic document summary

feat: add topic11 chunk provider interface

feat: add cross-artifact consistency verification

test: expand field operation and schema localization evidence

docs: publish topic5 hard-gap batch 1 evidence
```

Each commit must keep tests passing for the completed scope.

---

# 21. Final Verification Commands

At minimum, run:

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

backend\.venv\Scripts\python.exe scripts\eval_topic5_field_operations.py
backend\.venv\Scripts\python.exe scripts\eval_topic5_schema_localization.py
backend\.venv\Scripts\python.exe scripts\check_topic5_hard_gap_batch_1_gate.py

backend\.venv\Scripts\python.exe scripts\validate_schema_pack.py schema_packs/examples/announcement_doc
backend\.venv\Scripts\python.exe scripts\validate_schema_pack.py schema_packs/examples/event_notice_doc

backend\.venv\Scripts\python.exe scripts\run_topic5_inline_convert.py `
  --request examples/topic5_inline/announcement_convert_request.json `
  --out reports/topic5_inline_announcement_result.json `
  --create-package

backend\.venv\Scripts\python.exe scripts\run_topic5_inline_convert.py `
  --request examples/topic5_inline/event_notice_convert_request.json `
  --out reports/topic5_inline_event_notice_result.json `
  --create-package

Push-Location frontend
npm.cmd test
npm.cmd run build
Pop-Location
```

If script names differ because the repository has evolved, preserve the intent and document the actual commands used.

---

# 22. Definition of Done

This batch is complete only when all statements below are true:

1. `metadata_template` changes actual document metadata.
2. Metadata fields have deterministic source traces.
3. Three-level tag rules are configuration-driven.
4. No document-family tag table remains in backend code.
5. Mapping or validation problems affect only relevant chunks.
6. Document-level issues remain document-level.
7. A faithful, source-traced document summary exists.
8. JSON, Markdown, and chunks are verified against one canonical result.
9. Tampering and renderer inconsistency are detected.
10. Entity tags are passed through from upstream without invented IDs.
11. Topic 11 can be selected through a stable provider interface.
12. Invalid Topic 11 output is rejected or safely downgraded.
13. Field operations meet the declared `>=95%` threshold on an expanded fixture set.
14. Schema issue localization is `100%`.
15. Legacy requests and packages remain supported.
16. Full backend, lint, frontend, build, OpenAPI, SchemaPack, and package tests pass.
17. Reproducible evidence exists under `docs/交接/evidence/hard_gap_batch_1/`.
18. Documentation states limitations honestly.
19. No Topic 6, 7, 10, 11, 12, or Topic 1 core responsibility has been absorbed into Topic 5.

---

# 23. Final Codex Instruction

Proceed with implementation now.

Do not return only a design proposal. Inspect the current repository, establish the baseline, implement the workstreams in dependency order, run the tests, fix regressions, generate evidence, and summarize:

```text
changed files
new contracts
new tests
commands executed
test results
metric results
remaining limitations
commit SHAs
```

When a proposed detail conflicts with the current repository, preserve the mission, boundary, compatibility, and acceptance criteria of this document, then choose the smallest maintainable implementation that satisfies them.
