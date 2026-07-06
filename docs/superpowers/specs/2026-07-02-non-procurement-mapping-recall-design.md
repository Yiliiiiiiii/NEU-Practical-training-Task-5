# Non-procurement Mapping Recall Improvement Design

> **Historical specification:** Preserved for design rationale. Current status: [`../../project_status.md`](../../交接/project_status.md).

## Context

SchemaPack Agent currently evaluates 20 non-procurement documents across
`general_doc`, `meeting_doc`, and `policy_doc`. The frozen baseline is:

| Metric | Baseline | Phase-one target |
| --- | ---: | ---: |
| Average recall | 0.3494 | >= 0.50 |
| Review-required mappings | 145 | <= 115 |
| Required fields missing | 18 | <= 14 |
| Strict-pass documents | 4/20 | Improve where evidence permits |
| Badcase violations | 0 | 0 |
| Package verification | 20/20 | 20/20 |

The existing repository already provides the production pipeline, catalog
schemas and templates, badcase filtering, package verification, a
non-procurement evaluator, and regression tests. This work extends those
components in place. It does not introduce a second mapping pipeline.

## Goals

1. Establish a reproducible baseline → gap analysis → repair → regression
   evaluation loop for non-procurement documents.
2. Improve recall using traceable source evidence and deterministic rules.
3. Reduce unnecessary review-required mappings without auto-accepting fuzzy,
   ambiguous, or badcase-sensitive mappings.
4. Preserve procurement behavior, historical task snapshots, package validity,
   and the existing production boundary:
   `UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> ZIP`.
5. Report actual results honestly when phase-one thresholds are not reached.

## Non-goals

- Production-grade PDF, Word, or Excel parsing
- OCR, vector databases, model training, or automatic LLM rule activation
- Large-scale pipeline refactoring
- Removing required fields merely to improve strict-pass counts
- Editing generated evaluation JSON by hand
- Mapping values without source evidence

## Chosen Approach

Use an evidence-driven incremental implementation:

1. Freeze current evaluator output as the baseline.
2. Add an offline gap analyzer that reads generated package artifacts, gold
   mappings, and badcases.
3. Rank gaps by frequency, risk, evidence availability, and rule stability.
4. Implement only high-frequency, low-risk fixes using test-first changes.
5. Re-run the dedicated evaluator and analyzer after each functional group.
6. Adjust schema requirements only when the dataset demonstrates that a field
   is commonly absent and cannot be extracted reliably.

This approach favors explainability and regression safety over broad fuzzy
matching. It reuses existing evaluator and report helpers rather than creating
parallel HTTP or scoring abstractions.

## Architecture

### 1. Baseline and Evaluation Layer

The current `scripts/eval_non_procurement_doc.py` remains the reference
implementation for API-backed execution. A new
`scripts/eval_non_procurement_mapping.py` exposes the command and report
contract required by the execution guide while reusing existing evaluation
helpers and scoring rules.

The evaluator will:

- load all real-world UIR documents;
- select `general_doc`, `meeting_doc`, and `policy_doc`;
- import, create, and execute tasks through the existing API client;
- collect mapping, validation, metadata, and package verification results;
- compute per-document, per-type, and per-field metrics against gold labels;
- count strict pass, review-required, required missing, badcase violations,
  and package verification;
- compare results with the frozen baseline when `--baseline` is supplied;
- write deterministic JSON and Markdown reports.

Metrics must be derived from runtime artifacts. Reports are never treated as
inputs to production mapping decisions.

### 2. Gap Analysis Layer

`scripts/analyze_non_procurement_gaps.py` recursively discovers package
directories instead of assuming a fixed folder depth. It reads available
`metadata.json`, `mapping_report.json`, `validation_report.json`,
`content.json`, `canonical.json`, `content_organization_report.json`, and
`chunks.jsonl` files, then joins them with mapping gold labels and badcases.

Every diagnosed item belongs to one of six categories:

- `candidate_not_extracted`
- `alias_missing`
- `regex_missing`
- `schema_too_strict`
- `transform_type_error`
- `badcase_sensitive`

Classification is conservative. If available artifacts do not prove a more
specific cause, the analyzer records the evidence and leaves the item in the
least-assumptive category. Each item includes document type, document ID,
target field, source names and samples, source block IDs, review reason,
frequency, and recommended action.

The analyzer outputs both machine-readable JSON and a human-readable Markdown
report with the required sections and a do-not-auto-accept list.

### 3. Candidate Extraction Layer

`CandidateService` will preserve existing metadata, table, named-block,
aggregate-content, and meeting-date behavior. New extraction helpers add:

- heading/title candidates;
- `title_path` candidates when present in block attributes;
- conservative Chinese key/value candidates;
- list candidates grouped under recognized headings;
- paragraph-regex candidates for explicit dates, document numbers, phone
  numbers, issuers, and meeting dates.

All new candidates carry:

- `source_path`;
- non-empty `source_blocks`;
- a bounded `value_sample`;
- extraction origin in evidence;
- a confidence hint appropriate to the extraction mechanism.

Candidate extraction does not decide the final target field. Ambiguous text is
made available to mapping but is not promoted to accepted status merely
because a regex matched it.

### 4. Template and Mapping Layer

The existing production-like templates for `general_doc`, `meeting_doc`, and
`policy_doc` receive only aliases and regex rules supported by observed gaps.
Before a rule is added, its target field must exist in the corresponding
schema.

Rules are grouped by semantic intent:

- general documents: title, organization, dates, audience, conditions,
  materials, process, legal basis, and contact;
- meetings: title, date, location, attendees, chairperson, agenda, decisions,
  and action items;
- policies: title, issuer, number, publish/effective dates, scope, measures,
  requirements, application materials/process, contact, and legal basis.

High-risk pairs remain blocked or review-required. In particular:

- publish date is not an effective date without explicit evidence;
- chairperson and contact person are not attendees;
- organizer is not automatically issuer;
- budget or control price is not an awarded amount.

Template activation and effective-template resolution continue to preserve
historical task snapshots.

### 5. Schema and Validation Layer

Schema changes are a last resort. Core semantic groups remain required:

- general: title, one organization/source field, and one content/process field;
- meeting: title, one date field, and one agenda/decision/summary field;
- policy: title, one issuer field, one publication identifier/date field, and
  one measures/requirements/content field.

If the existing schema model supports `required_any`, it will be used through
the existing validation path. Otherwise, a small metadata-hint extension may
be added without redesigning validation. Optional-field changes require
dataset evidence and are recorded in
`reports/non_procurement_schema_adjustments.md`, including affected documents,
risk, and reviewer notes.

Procurement and contract schemas are unchanged.

### 6. Transform Layer

`TransformService` gains field-aware normalization:

- Chinese, dotted, and slash-separated full dates to ISO dates;
- recognized array fields split on Chinese enumeration punctuation,
  semicolons, or newlines;
- phone whitespace normalized without accepting contact-person names;
- document numbers preserved as text.

Dates without a year are not guessed. They produce an error or warning that
keeps the item reviewable. Normalization failures retain the original value in
diagnostics rather than silently fabricating a canonical value.

### 7. Badcase Safety Layer

The real-world badcase set is extended with date, person, organization, and
procurement-amount confusion pairs. Existing mapping filters remain the
enforcement point. Alias and regex enhancements must not bypass them.

Badcase regression verifies both outcomes:

- the forbidden pair is never high-confidence auto-accepted;
- an otherwise plausible candidate may remain review-required with explicit
  `badcase_blocked` evidence.

## Data Flow

```text
Real-world UIR
  -> API task execution
  -> package artifacts
  -> baseline evaluator
  -> gap analyzer + gold + badcases
  -> ranked, evidence-backed fix list
  -> TDD changes to candidate/template/transform/validation
  -> API task re-execution
  -> evaluator + gap analyzer
  -> acceptance report and documentation
```

Generated artifacts are outputs of execution. Code, templates, schemas, gold
labels, and badcases are the controlled inputs.

## Error Handling

- Missing package roots, gold files, or malformed required JSON produce a
  non-zero exit with a clear path-specific error.
- Optional package artifacts may be absent; the analyzer records reduced
  diagnostic confidence instead of crashing.
- Unknown document types are ignored and counted separately in diagnostics.
- Invalid regex configuration fails template loading or its targeted test.
- Unparseable transform values remain errors or warnings and are not silently
  accepted.
- HTTP evaluator failures identify the document and stage, preserve completed
  case results, and appear in `failed_cases`.
- Report directories are created by the scripts; writes use UTF-8 and stable
  ordering where practical.

## Testing Strategy

All production behavior changes follow red-green-refactor:

1. Add focused failing tests for candidate extraction, templates, validation,
   transforms, badcases, gap analysis, and evaluation report generation.
2. Confirm each test fails for the missing behavior.
3. Add the smallest implementation required to pass.
4. Run the focused test file, then the relevant existing regression tests.

Required regression coverage includes:

- headings, title paths, Chinese key/value text, headed lists, paragraph regex,
  empty blocks, evidence preservation, and noise filtering;
- alias and regex targets existing in their schemas;
- forbidden pairs remaining blocked/review-required;
- snapshot isolation after template changes;
- core required fields still failing when absent;
- optional and required-any behavior;
- Chinese date, array, phone, and document-number normalization;
- analyzer classification and deterministic JSON/Markdown structure;
- evaluator filtering, scoring, baseline deltas, and failed-case reporting;
- unchanged procurement mapping and badcase behavior.

Final verification runs:

- full backend pytest;
- backend ruff;
- frontend clean install and build;
- `scripts/verify_all.py --check-openapi`;
- real-world UIR, mapping, and non-procurement evaluators;
- non-procurement gap analysis;
- content strategy, summary faithfulness, tag quality, review knowledge growth,
  and downstream contract regressions.

## Delivery and Reporting

Implementation is divided into reviewable phases:

1. Baseline artifacts and tests for report contracts
2. Gap analyzer and improvement plan
3. Candidate extraction
4. Templates and regex rules
5. Evidence-backed schema/validation adjustments
6. Transform normalization
7. Badcases
8. Dedicated evaluator
9. Final reports and required documentation
10. Full verification

Each phase records changed files, commands, results, and remaining risk.
Commits are scoped by functional phase and do not include the user's unrelated
untracked guide documents.

The acceptance report compares actual metrics with phase-one thresholds. A
threshold is marked passed only when the fresh evaluator output proves it.
Otherwise, the report names the remaining high-frequency gaps and recommends
the next bounded iteration.
