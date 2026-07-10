# SchemaPack Contract

## Definition

A SchemaPack is the versioned external configuration contract for Topic 5. It declares the target schema, metadata template, mapping rules, content organization parameters, optional router hints, deterministic output assertions, examples, and badcases.

The canonical Topic 5 input consists of normalized UIR, target schema, metadata template, mapping rules, and content organization parameters. A SchemaPack packages these configuration assets for reusable execution.

## Canonical Layout

Each migrated pack contains `schema_pack.yaml`, `target_schema.json`, `metadata_template.json`, `mapping_rules.yaml`, `content_org.yaml`, optional `router_rules.yaml`, optional `output_assertions.yaml`, positive examples, and badcases. Asset file names are not guessed: runtime loading follows the references under `schema_pack.yaml.assets`.

The runtime contract source of truth is `backend/app/schemas/schema_pack_contract.py`. The generated external schema is `schema_packs/schema_pack_contract.schema.json`.

## Manifest Fields

`schema_pack.yaml` declares identity, semantic version, compatibility, relative asset references, execution defaults, supported input, and an explicit claim boundary. Unknown fields are rejected. Absolute paths, `..` traversal, and resolved paths outside the pack are rejected.

## Versioning

- MAJOR: incompatible contract or output behavior.
- MINOR: backward-compatible field, assertion, or configuration addition.
- PATCH: correction that does not intentionally change output behavior.

SchemaPack versions use `MAJOR.MINOR.PATCH`; contract versions use `MAJOR.MINOR`.

## Loading And Validation

`SchemaPackService` uses `yaml.safe_load` and loads every referenced asset through the manifest. `SchemaPackContractValidator` validates the manifest, path safety, required files, typed assets, cross-file IDs, target-field references, JSON paths, regex patterns, and fixture JSON.

```powershell
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc --out reports/schema_pack_contract_announcement_doc.json
python scripts/eval_schema_pack_contracts.py --all-examples --verify-package --out reports/schema_pack_contract_all.json --markdown reports/schema_pack_contract_all.md
python scripts/check_schema_pack_contract_gate.py --fail-on-gate
```

## Compatibility

Output assertions are optional. Existing Package 1.1 deliverables and legacy Topic 5 requests remain supported.

Registered execution runs the complete SchemaPack validator before mapping, then checks the current SchemaPack agent version (`1.0.0`), the selected document's UIR version, and Package contract `1.1` against the manifest compatibility declaration. A terminal task cannot be executed again; reruns require a new task so prior assertion evidence remains immutable.

The assertion report is a task artifact by default. When explicitly enabled, `reports/conversion_assertion_report.json` is added to Package 1.1 as a checksummed optional manifest entry.

The Phase 3 gate verifies Package 1.1 in both forms: one example without the optional assertion report and one with a `required=false`, `conversion_assertion_report`, `application/json` manifest entry.

## Hard-Gap Batch 1 Configuration

`metadata_template.json` is operational configuration, not descriptive metadata. Fields
use strict types and safe source roots only. `content_org.yaml` may configure audited
content-tag predicates, whitelisted management metadata, built-in local quality facts,
document-summary behavior, and `internal` or `topic11` chunk providers. Unknown keys and
malformed rules are rejected by the strict models.

Transform rules execute a fixed allowlist: rename, merge, split, trim, date/datetime
normalization, enum mapping, and defaults. Source access is limited to safe UIR metadata
paths and exact block text paths. Python expressions, wildcards, environment lookups, and
credential paths are not executable.

The announcement and event-notice example packs are golden fixtures for metadata effects,
configured tags, local quality tags, extractive summaries, entity passthrough, Markdown
anchors, artifact consistency, and final manifest verification.

## Scope Boundary

Conversion output assertions are deterministic SchemaPack-scoped checks over Topic 5 converted output. They complement target-schema validation but do not implement Topic 6 quality scoring, grading, semantic fidelity evaluation, or routing recommendations.

Non-goals:

- no quality score;
- no quality grade;
- no publication route;
- no semantic fidelity judgment;
- no LLM-as-Judge;
- no Topic 11 retrieval optimization.
