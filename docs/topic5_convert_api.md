# Topic 5 Inline Convert API

## 1. Purpose

The Topic 5 runtime converts a normalized UIR document into a schema-governed standard package. The public input contract is:

```text
UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config
```

The runtime starts from UIR JSON. It does not parse raw PDF, Word, Excel, images, or scanned documents in production runtime.

## 2. Endpoints

```text
POST /api/v1/topic5/convert
POST /api/v1/topic5/convert/package
```

`/convert` returns inline artifacts. `/convert/package` also creates a manifest, package metadata, verifier report, and ZIP path.

## 3. Request

Preferred request field:

```json
{
  "uir": {},
  "target_schema": {},
  "mapping_rules": {},
  "metadata_template": {},
  "content_organization": {},
  "options": {}
}
```

Backward-compatible request field:

```json
{
  "uir": {},
  "target_schema": {},
  "mapping_template": {},
  "metadata_template": {},
  "content_organization": {},
  "options": {}
}
```

`mapping_rules` is the public Topic 5 term. `mapping_template` remains accepted as a legacy alias because the current backend loads mapping rules into the internal `MappingTemplate` model.

If both fields are supplied, they must be identical. Conflicting dual inputs are rejected with validation error 422.

## 4. Response

The response includes:

```text
task_id
status
schema_id
template_id
content_json
content_markdown
chunks
mapping_report
transform_report
validation_report
content_organization_report
manifest
package_zip_path
package_metadata
verifier_report
```

`mapping_report.summary.mapping_input_name` records whether the accepted request used `mapping_rules` or legacy `mapping_template`.

## 5. Status Semantics

```text
completed:
  No mapping review items.
  No required unmapped fields.
  Validation passed.
  Package verifier passed if package mode is used.

review_required:
  At least one mapping requires human review.
  Or at least one required target field is unmapped.
  Or validation did not pass.

failed:
  Package verifier failed.
  Or unrecoverable conversion error occurred.
```

## 6. Runtime Non-goals

The project does not claim production-grade blind recall 0.85. The current stronger mapping metric is assisted recall 0.861, while auto recall still needs improvement.

LLM assistance is disabled by default. If enabled in future extensions, it must remain report-only unless a separate explicit governance workflow accepts the result. LLM output must not directly activate schema, template, mapping rules, or production catalog entries.

## 7. Phase 3 Output Assertions

Inline requests may add an optional `output_assertions` object conforming to `schema_packs/output_assertions_contract.schema.json`. Responses add optional `conversion_assertion_report` evidence.

```json
{
  "strict_output_assertions": false,
  "include_assertion_report_in_package": false
}
```

Warnings do not fail conversion. Assertion errors produce `review_required` by default; strict assertion errors produce `failed`. Requests without assertions retain existing behavior.

Registered task creation may set `schema_pack_id`. The task then loads target schema, metadata template, mapping rules, content organization parameters, optional router hints, and output assertions from `schema_pack.yaml` references.

Output assertions are optional. Existing Package 1.1 deliverables and legacy Topic 5 requests remain supported.

Conversion output assertions are deterministic SchemaPack-scoped checks over Topic 5 converted output. They complement target-schema validation but do not implement Topic 6 quality scoring, grading, semantic fidelity evaluation, or routing recommendations.
