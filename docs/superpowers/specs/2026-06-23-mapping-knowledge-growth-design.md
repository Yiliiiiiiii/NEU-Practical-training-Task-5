# Mapping Knowledge Growth Design

This design adds a controlled growth loop for SchemaPack Agent after the Phase 10 acceptance baseline. It is a topic 5 productization extension, not a replacement for the core conversion pipeline. The extension helps the project adapt to more real UIR, Schema, and Mapping Template variants by turning reviewed mapping evidence into reusable mapping knowledge and evaluation assets.

## Scope

The growth loop is limited to topic 5 responsibilities:

1. Improve field candidate mapping through approved aliases, regex rules, enum maps, defaults, and transform rules.
2. Build human-reviewed evaluation cases and badcases from real runs.
3. Let LLMs propose mapping knowledge, confidence, evidence, and risk flags.
4. Require human approval before any learned rule affects production mapping.
5. Preserve deterministic replay by versioning every accepted knowledge pack.

The extension must not parse raw PDF, Word, Excel, image, OCR, or layout inputs. It must not perform cleaning, normalization, entity linking, full quality scoring, full RAG, model training, or automatic high-quality QA generation.

## Goals

1. Collect real UIR runs without treating raw runtime outputs as gold fixtures.
2. Extract learning candidates from review decisions, failed mappings, unmapped required fields, low-confidence mappings, LLM suggestions, and conversion errors.
3. Support human approval, rejection, or editing of each learning candidate.
4. Publish approved items into versioned mapping knowledge packs scoped by domain, schema, template, and field.
5. Run regression evaluation before a knowledge pack is activated.
6. Keep a clear audit trail from real run to review decision to approved rule to evaluation result.
7. Improve future mappings while preserving the rule-first, LLM-fallback, human-review contract.

## Non-Goals

- No direct model training or fine-tuning.
- No automatic production rule merge from LLM output.
- No promise of 100% automatic semantic mapping.
- No bypass of manual review for unresolved, conflicting, low-confidence, or high-risk mappings.
- No replacement for topic 2 parsing, topic 3 cleaning, topic 4 normalization, or topic 6/12 final quality scoring.
- No use of unreviewed real documents as public accuracy evidence.

## Architecture

The feature adds three bounded subsystems.

`RealRunCollector` stores metadata about real conversion runs. It records input hash, schema/template versions, mapping report summary, LLM audit summary, review outcomes, validation status, consistency status, and package status. It references runtime files under `storage/` but does not copy raw UIR into versioned fixtures by default.

`LearningCandidateService` derives reviewable learning candidates from real runs. Candidate types include `alias_candidate`, `regex_candidate`, `enum_map_candidate`, `default_candidate`, `transform_candidate`, `gold_mapping_candidate`, and `badcase_candidate`. Each candidate includes source evidence, suggested target field, confidence, risk level, generating method, and the task/run IDs that produced it.

`KnowledgePackService` publishes approved candidates into versioned knowledge packs. A knowledge pack is an overlay on top of the existing Mapping Template. It can add aliases, regex rules, enum maps, defaults, or transform rules, but only after binding validation against the target schema and a successful regression run.

LLM assistance remains behind the existing LLM client boundary. The LLM may propose learning candidates from approved review history and failure summaries. It must not write Mapping Template records, canonical fields, content outputs, package files, or evaluation gold directly.

## Data Model

New persistent records:

- `real_runs`: one row per attempted real workflow run, linked to task, document, schema, template, input hash, status, and report paths.
- `learning_candidates`: proposed reusable knowledge items with status `pending`, `approved`, `rejected`, or `superseded`.
- `knowledge_packs`: versioned approved overlays with scope, parent version, activation status, and regression report path.
- `knowledge_pack_items`: normalized approved rules or evaluation assets inside a pack.

Runtime artifacts stay in `storage/`. Human-reviewed, sanitized evaluation assets can be exported into `examples/eval/real/` or `examples/badcases/real/` only after explicit approval.

## Workflow

Real run intake:

`UIR + Schema + Template -> task -> candidates -> mapping -> review -> convert -> package -> real_run summary`

Learning extraction:

`real_run summary + review records + reports -> learning candidates -> human review queue`

Knowledge publishing:

`approved candidates -> schema/template binding validation -> proposed knowledge pack -> regression evaluation -> activate or reject`

Evaluation growth:

`approved gold_mapping_candidate/badcase_candidate -> sanitized fixture export -> evaluation CLI -> trend report`

Runtime reuse:

`active knowledge pack + base template -> effective mapping template -> rule-first mapping -> optional LLM fallback -> human review`

## Review And Approval Rules

Every learning candidate starts as `pending`.

Approvers can approve, reject, or edit a candidate. Edited candidates keep the original proposal and the final approved form. Rejections require a reason. Approval records include reviewer, timestamp, task IDs, input hash, source evidence, and affected target fields.

High-risk candidates require stricter handling:

- Regex rules must show matched examples and non-matched counterexamples when available.
- Transform rules must pass source path existence checks on the originating run.
- Defaults for required fields must be marked as business-approved.
- LLM-generated candidates are always high-risk until a human approves them.

## Effective Template Resolution

The mapper receives an effective template, not a hidden mutable global rule set.

Effective template resolution order:

1. Base Mapping Template selected by the task.
2. Active knowledge packs whose scope matches schema/template/domain.
3. Task-specific overrides, if any.

The resolved effective template is written into the task config snapshot with pack IDs and versions. This preserves replayability and makes it possible to compare runs before and after a knowledge pack.

## Evaluation And Metrics

The system reports growth using internal, reviewed evidence only:

- mapping precision, recall, and F1 on approved evaluation fixtures
- review-required rate
- unmapped required field count
- LLM suggestion acceptance rate
- rule coverage by method
- regression deltas before and after a knowledge pack
- badcase pass/fail status by category
- confidence bucket accuracy

Public accuracy claims can only use frozen, human-reviewed fixtures. Demo samples and unreviewed real runs are operational evidence, not accuracy evidence.

## Error Handling

Invalid learning candidates are rejected with structured reasons. Knowledge pack publication fails if a rule references an unknown target field, creates duplicate conflicting rules, breaks schema binding, or regresses evaluation beyond configured thresholds.

LLM proposal failures are recorded as proposal errors and do not fail the main mapping workflow. If an active knowledge pack cannot be resolved, the task must either fall back to the base template with an explicit warning or stop before mapping, depending on the configured strictness.

## Security And Privacy

Real UIR may contain sensitive content. The default storage path keeps real run artifacts under runtime `storage/`, not versioned `examples/`. Exporting a real case to evaluation fixtures requires a sanitization step and explicit human approval.

LLM proposal prompts should send only bounded field names, types, value samples, review outcomes, and sanitized context. Raw full UIR text must not be sent unless explicitly enabled by configuration.

## Testing

Backend tests must cover:

1. Learning candidates are derived from review changes, LLM fallback mappings, unmapped required fields, and failed transform rules.
2. Pending candidates do not affect mapping output.
3. Approved alias and regex candidates create a knowledge pack that changes future effective-template mapping.
4. Unknown target fields or invalid transform candidates are rejected.
5. LLM proposals remain pending and cannot activate without human approval.
6. Effective template resolution records knowledge pack IDs and versions in config snapshots.
7. Regression evaluation blocks activation when metrics fall below threshold.
8. Sanitized fixture export refuses raw real-run artifacts without approval.

Frontend tests must cover:

1. A learning review queue lists pending candidates with source evidence and risk.
2. Users can approve, reject, or edit a candidate.
3. Knowledge pack activation shows regression results before activation.
4. Real-run metrics distinguish operational runs from frozen evaluation evidence.

## Acceptance

The feature is accepted when a reviewer can run several real UIR tasks, review mappings, generate learning candidates, approve a small alias/regex knowledge pack, rerun mapping with the pack active, and see improved mapping or reduced review rate without losing replayability or audit evidence.

The acceptance report must clearly state that the feature grows mapping knowledge and evaluation assets only. It must not claim model training, autonomous data cleaning, raw document parsing, or full RAG capability.
