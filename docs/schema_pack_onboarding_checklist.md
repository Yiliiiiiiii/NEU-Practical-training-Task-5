# SchemaPack Onboarding Checklist

## 1. Create SchemaPack Directory

- [ ] Create `schema_packs/examples/<schema_id>/`.
- [ ] No core backend code is modified for normal SchemaPack onboarding.

## 2. Define Target Schema

- [ ] `target_schema.json` defines `schema_id`, `version`, and non-empty `fields`.
- [ ] Required fields are truly required by downstream consumers.

## 3. Define Metadata Template

- [ ] `metadata_template.json` defines `template_id`, `schema_id`, and `version`.
- [ ] Metadata defaults are safe and deterministic.

## 4. Define Mapping Rules

- [ ] `mapping_rules.yaml` contains `schema_id`, `template_id`, and `version`.
- [ ] `mapping_rules.yaml` contains aliases for every required field.
- [ ] Regex rules exist for values that must be extracted from free text.
- [ ] Negative pairs exist for known confusing fields.

## 5. Define Content Organization Config

- [ ] `content_org.yaml` defines chunk strategy and tag policy.
- [ ] Chunk sizes fit the expected downstream RAG or export consumer.

## 6. Optional Router Rules

- [ ] `router_rules.yaml` is present when automatic recommendation is desired.
- [ ] Router rules are only recommendations and not capability boundaries.

## 7. Add Example UIR

- [ ] At least one example UIR is provided.
- [ ] The example UIR contains enough evidence for all required fields.

## 8. Add Inline Convert Request

- [ ] Request uses `mapping_rules` as the preferred public field.
- [ ] Legacy `mapping_template` is used only in backward-compatibility tests.

## 9. Run Inline Conversion

- [ ] Inline conversion passes.
- [ ] `mapping_report.summary.required_unmapped_count` is 0.
- [ ] `mapping_report.summary.review_required_count` is 0.

## 10. Run Package Verification

- [ ] Package verifier passes.
- [ ] Manifest and checksum outputs are generated.

## 11. Add Badcases

- [ ] Negative examples exist for common confusing fields.
- [ ] Badcases do not require LLM auto-acceptance.

## 12. Add Regression Test

- [ ] Regression test asserts `status == "completed"`.
- [ ] Regression test asserts package verifier passed.
- [ ] Regression test asserts no LLM suggestions were auto accepted.

## 13. Update Documentation

- [ ] Documentation states the SchemaPack is an example configuration, not a system boundary.
- [ ] Demo or handoff docs include the new no-code onboarding example.

