# Phase 3 Execution Plan: SchemaPack Contract and Quality Rules

Version: 1.0  
Target branch recommendation: `feat/schema-pack-quality-contract`  
Base branch recommendation: merge/rebase from `feat/topic5-mapping-benchmark` after Phase 2 acceptance  
Primary objective: turn SchemaPack from a collection of example configuration files into a versioned, testable, quality-governed data contract.

---

## 0. Carry-over Fixes from Phase 2 Acceptance

Before implementing new Phase 3 features, fix the following issues found during Phase 2 acceptance. These are part of Phase 3 and must be executed first.

---

### 0.1 Fix `validate_schema_pack.py` regex validation

#### Problem

The current negative-pair regex check effectively does this:

```python
elif not re.compile(str(item["source_pattern"])):
    errors.append(...)
```

`re.compile()` returns a truthy regex object when valid, and raises `re.error` when invalid. Therefore invalid regex patterns may crash the validator instead of being reported cleanly.

#### File to modify

```text
scripts/validate_schema_pack.py
```

#### Required change

Replace the current regex validation block with:

```python
try:
    re.compile(str(item["source_pattern"]))
except re.error as exc:
    errors.append(
        f"negative_pairs[{index}].source_pattern is invalid: {exc}"
    )
```

#### Required test

Update or add:

```text
backend/tests/test_schema_pack_contract_validation.py
```

Test case:

```python
def test_validate_schema_pack_reports_invalid_negative_pair_regex(tmp_path):
    # create/copy a pack and set negative_pairs[0].source_pattern = "["
    result = validate_schema_pack(pack_dir)
    assert result["status"] == "failed"
    assert any("source_pattern is invalid" in item for item in result["errors"])
```

#### Acceptance criteria

```text
[ ] Invalid negative-pair regex does not crash the validator.
[ ] Invalid regex is reported as a normal validation error.
```

---

### 0.2 Fix or rename mapping evaluator `package_pass_rate`

#### Problem

The Phase 2 evaluator currently calculates `package_passed` without actually creating and verifying a package. It sets package success from response status only. This makes `package_pass_rate` misleading.

#### Files to modify

```text
scripts/eval_topic5_standard_uir_mapping.py
scripts/check_topic5_mapping_quality_gate.py
backend/tests/test_topic5_standard_uir_eval.py
```

#### Required behavior

Use two separate metrics:

```text
conversion_pass_rate:
  response.status in {"completed", "review_required"}

package_verifier_pass_rate:
  actual verifier pass rate when package verification is enabled
```

#### Required CLI update

Add:

```text
--verify-package
```

Default behavior:

```text
--verify-package false for fast local iteration
--verify-package true in final gate scripts and committed evidence reports
```

Recommended implementation:

```python
response = Topic5ConversionService(tmp).convert(
    request,
    create_package=verify_package,
)

conversion_passed = response.status in {"completed", "review_required"}

package_verifier_passed = (
    response.verifier_report.get("passed") is True
    if verify_package and response.verifier_report
    else None
)
```

In aggregation:

```python
conversion_pass_rate = passed_conversion_count / dataset_size
package_verifier_pass_rate = (
    passed_verifier_count / verified_count
    if verified_count else None
)
```

#### Required report changes

Update JSON reports to use:

```json
{
  "conversion_pass_rate": 1.0,
  "package_verifier_pass_rate": 1.0,
  "package_verified_count": 60
}
```

Do not use `package_pass_rate` unless it means actual verifier pass rate.

#### Acceptance criteria

```text
[ ] Reports no longer imply package verification when no package was generated.
[ ] Final quality gate uses actual package verifier results.
[ ] Old report field is removed or explicitly deprecated.
```

---

### 0.3 Add per-schema quality gate warnings/failures

#### Problem

The Phase 2 global assignment aggregate metrics pass, but some individual schema families may have weaker precision than the aggregate. A high aggregate can hide weak families.

#### Files to modify

```text
scripts/check_topic5_mapping_quality_gate.py
scripts/eval_topic5_standard_uir_mapping.py
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
docs/交接/topic5_mapping_quality_phase2.md
```

#### Required thresholds

Add per-schema thresholds:

```text
per_schema_auto_precision >= 0.85
per_schema_auto_recall >= 0.85
per_schema_badcase_violations = 0
per_schema_required_missing = 0
```

Default gate policy:

```text
aggregate thresholds are hard fail
per-schema badcase/required-missing are hard fail
per-schema precision/recall below threshold are warnings in Phase 3, then hard fail in later Phase 4 if desired
```

Recommended report fields:

```json
{
  "warnings": [
    {
      "type": "schema_precision_below_recommended_threshold",
      "schema_id": "policy_doc",
      "auto_precision": 0.80,
      "threshold": 0.85
    }
  ],
  "failed_checks": []
}
```

#### Acceptance criteria

```text
[ ] Gate report includes aggregate metrics and per-schema metrics.
[ ] Per-schema weak spots are visible and not hidden by aggregate pass.
[ ] Documentation states which threshold is hard fail and which is warning.
```

---

### 0.4 Tighten MappingRepairService auto-accept behavior

#### Problem

`MappingRepairService` currently repairs an unmapped required field when score >= review_threshold and creates a mapping with `need_review=False`. This can over-accept low-confidence repairs.

#### Files to modify

```text
backend/app/services/mapping_repair_service.py
backend/tests/test_mapping_repair_service.py
```

#### Required behavior

Use two thresholds:

```text
repair_auto_accept_threshold default 0.82
repair_review_threshold default 0.62
```

Behavior:

```text
score >= repair_auto_accept_threshold:
  add accepted repair mapping

repair_review_threshold <= score < repair_auto_accept_threshold:
  add review_required repair item, not accepted mapping

score < repair_review_threshold:
  remain unmapped
```

#### Required report fields

```json
{
  "accepted_repair_fields": [],
  "review_repair_fields": [],
  "unrepaired_fields": []
}
```

#### Acceptance criteria

```text
[ ] Repair does not auto-accept below auto threshold.
[ ] Low-confidence repair candidates go to review_required.
[ ] Existing tests are updated.
```

---

### 0.5 Update Phase 2 documentation claim boundary

#### Problem

Phase 2 reports may show strong benchmark-level performance. Documentation must still state that this is benchmark-level and not production-grade.

#### Files to modify

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/topic5_mapping_quality_phase2.md
reports/topic5_mapping_quality_gate_report.md
```

#### Required wording

Use this statement:

```text
The project can claim Topic 5 benchmark-level auto mapping recall >= 0.85 within the declared standard UIR benchmark scope. This is not a production shadow/blind claim and not an arbitrary-schema production claim.
```

Do not use:

```text
production-grade auto mapping
arbitrary-schema 0.85
production blind recall passed
```

#### Acceptance criteria

```text
[ ] Documentation distinguishes benchmark-level claim from production-grade claim.
[ ] No overclaim phrase remains.
```

---

# 1. Phase 3 Goal

Phase 3 turns SchemaPack into a stronger contract.

Current SchemaPack examples already include:

```text
target_schema.json
metadata_template.json
mapping_rules.yaml
content_org.yaml
router_rules.yaml
```

Phase 3 expands this into a data-contract-style structure:

```text
schema_pack.yaml
target_schema.json
metadata_template.json
mapping_rules.yaml
content_org.yaml
quality_rules.yaml
router_rules.yaml
examples/
tests/
badcases/
```

The system must be able to:

```text
1. Validate a SchemaPack as a complete contract.
2. Run field-level and document-level quality rules after conversion.
3. Generate quality_report.json.
4. Fail, warn, or review according to quality rule severity.
5. Evaluate SchemaPack examples and badcases.
6. Preserve Package 1.1 compatibility while optionally supporting Package 1.2 quality artifacts.
```

---

# 2. Phase 3 Scope

## 2.1 In scope

```text
- SchemaPack manifest contract
- quality_rules.yaml contract
- QualityRuleService
- quality_report generation
- SchemaPack contract validator expansion
- SchemaPack quality evaluation script
- documentation updates
- tests for rules and validator
- optional package inclusion of quality_report
```

## 2.2 Out of scope

```text
- Frontend workbench
- LLM rule generation
- automatic activation of rules
- production monitoring
- multi-tenant permission system
- full data catalog UI
```

---

# 3. Recommended Branching

```powershell
git checkout feat/topic5-mapping-benchmark
git pull
git checkout -b feat/schema-pack-quality-contract
```

Recommended commits:

```text
fix: harden phase2 quality evidence
feat: add schema pack manifest contract
feat: add quality rule service
feat: add schema pack quality evaluator
docs: document schema pack quality contract
```

---

# 4. Target Directory Structure

Each SchemaPack should support this structure:

```text
schema_packs/examples/<schema_pack_id>/
  schema_pack.yaml
  target_schema.json
  metadata_template.json
  mapping_rules.yaml
  content_org.yaml
  quality_rules.yaml
  router_rules.yaml
  examples/
    example_001_uir.json
    example_001_request.json
    expected_content.json
  tests/
    expected_mapping.json
    expected_quality.json
  badcases/
    negative_pairs.jsonl
    badcase_001_uir.json
```

For Phase 3, update at least:

```text
schema_packs/examples/announcement_doc/
schema_packs/examples/event_notice_doc/
```

Optionally add minimal manifests for historical packs:

```text
policy_doc
meeting_doc
procurement_doc
general_doc
contract_doc
```

---

# 5. Task 3.1: Add `schema_pack.yaml`

## 5.1 Files to create

```text
schema_packs/examples/announcement_doc/schema_pack.yaml
schema_packs/examples/event_notice_doc/schema_pack.yaml
```

## 5.2 Required fields

Example:

```yaml
schema_pack_id: announcement_doc
schema_pack_version: 1.0.0
display_name: Announcement Document
description: Topic 5 example SchemaPack for public announcements.
status: example
owner: course-team

runtime:
  min_agent_version: 1.0.0
  package_contract: "1.1"
  quality_contract: "1.0"

assets:
  target_schema: target_schema.json
  metadata_template: metadata_template.json
  mapping_rules: mapping_rules.yaml
  content_org: content_org.yaml
  quality_rules: quality_rules.yaml
  router_rules: router_rules.yaml

supported_input:
  uir_version: "1.0"
  languages:
    - zh-CN
    - en-US
  source_formats:
    - standard_uir

quality_policy:
  fail_on_error: true
  review_on_warning: false
  include_quality_report_in_package: false

claim_boundary:
  description: Example configuration and benchmark baseline, not system capability boundary.
  production_ready: false
```

## 5.3 Acceptance criteria

```text
[ ] schema_pack.yaml exists for announcement_doc.
[ ] schema_pack.yaml exists for event_notice_doc.
[ ] schema_pack.yaml references all asset files.
[ ] SchemaPack validator checks schema_pack.yaml.
```

---

# 6. Task 3.2: Extend SchemaPack Contract JSON Schema

## 6.1 File to modify

```text
schema_packs/schema_pack_contract.schema.json
```

## 6.2 Required contract additions

Add validation for:

```text
schema_pack_id
schema_pack_version
display_name
description
status
owner
runtime
assets
supported_input
quality_policy
claim_boundary
```

Also add a contract section for quality rules:

```text
quality_rules_file
quality_rule_schema_version
```

## 6.3 Acceptance criteria

```text
[ ] schema_pack_contract.schema.json documents schema_pack.yaml.
[ ] It lists required asset files.
[ ] It describes quality rule contract.
```

---

# 7. Task 3.3: Add `quality_rules.yaml`

## 7.1 Files to create

```text
schema_packs/examples/announcement_doc/quality_rules.yaml
schema_packs/examples/event_notice_doc/quality_rules.yaml
```

## 7.2 Contract format

```yaml
schema_id: announcement_doc
version: 1.0.0

rules:
  - rule_id: title_required
    field: title
    rule: non_empty
    severity: error
    message: Title must not be empty.

  - rule_id: publish_date_format
    field: publish_date
    rule: date_format
    severity: error
    format: "%Y-%m-%d"
    message: Publish date must be normalized to YYYY-MM-DD.

  - rule_id: body_min_length
    field: body
    rule: text_min_length
    severity: warning
    min_length: 10
    message: Body is unusually short.

  - rule_id: source_url_optional_format
    field: source
    rule: url_like
    severity: warning
    optional: true
    message: Source should be URL-like when present.
```

Event notice example:

```yaml
schema_id: event_notice_doc
version: 1.0.0

rules:
  - rule_id: title_required
    field: title
    rule: non_empty
    severity: error

  - rule_id: organizer_required
    field: organizer
    rule: non_empty
    severity: error

  - rule_id: event_time_format
    field: event_time
    rule: datetime_format
    severity: error
    formats:
      - "%Y-%m-%d %H:%M"
      - "%Y-%m-%dT%H:%M:%S"

  - rule_id: body_min_length
    field: body
    rule: text_min_length
    severity: warning
    min_length: 10
```

## 7.3 Supported severities

```text
error:
  quality_report.passed becomes false

warning:
  quality_report.passed can remain true, but report shows warning

review:
  quality_report.passed can remain true, but conversion status should become review_required if quality review is enabled
```

## 7.4 Required supported rules in Phase 3

Implement these first:

```text
non_empty
date_format
datetime_format
text_min_length
regex_match
enum_allowed
number_range
url_like
array_min_items
cross_field_not_equal
```

Optional later:

```text
organization_like
phone_like
email_like
not_future
required_if
forbidden_equal_to_field
```

Do not implement too many advanced rules at once.

---

# 8. Task 3.4: Implement QualityRuleService

## 8.1 Files to add

```text
backend/app/services/quality_rule_service.py
backend/app/schemas/quality_rules.py
backend/tests/test_quality_rule_service.py
```

## 8.2 Data models

Add Pydantic models:

```python
class QualityRule(StrictBaseModel):
    rule_id: str
    field: str
    rule: str
    severity: Literal["error", "warning", "review"] = "error"
    message: str | None = None
    optional: bool = False
    format: str | None = None
    formats: list[str] = Field(default_factory=list)
    pattern: str | None = None
    allowed_values: list[Any] = Field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    min_length: int | None = None
    other_field: str | None = None


class QualityRulesConfig(StrictBaseModel):
    schema_id: str
    version: str = "1.0.0"
    rules: list[QualityRule] = Field(default_factory=list)


class QualityIssue(StrictBaseModel):
    rule_id: str
    field: str
    rule: str
    severity: str
    message: str
    value_preview: str | None = None


class QualityReport(StrictBaseModel):
    task_id: str
    schema_id: str
    passed: bool
    error_count: int
    warning_count: int
    review_count: int
    issues: list[QualityIssue]
    summary: dict[str, Any] = Field(default_factory=dict)
```

## 8.3 Service behavior

```python
class QualityRuleService:
    def validate(
        self,
        *,
        task_id: str,
        schema_id: str,
        content_json: dict[str, Any],
        rules_config: QualityRulesConfig,
    ) -> QualityReport:
        ...
```

Input data should come from:

```python
data = content_json.get("data", {})
metadata = content_json.get("metadata", {})
```

Search field value in this order:

```text
content_json["data"][field]
content_json["metadata"][field]
None
```

## 8.4 Rule behavior

### non_empty

Fail if:

```text
value is None
value == ""
value == []
```

### date_format

Use `datetime.strptime(value, format)`.

If `format` missing, default:

```text
%Y-%m-%d
```

### datetime_format

Try each format in `formats`; if absent use:

```text
%Y-%m-%d %H:%M
%Y-%m-%dT%H:%M:%S
%Y-%m-%dT%H:%M:%S%z
```

### text_min_length

Fail if string length < `min_length`.

### regex_match

Fail if `pattern` does not match string value.

### enum_allowed

Fail if value not in `allowed_values`.

### number_range

Fail if numeric value outside `[min_value, max_value]`.

### url_like

Pass if value starts with:

```text
http://
https://
```

If `optional=true` and missing, pass.

### array_min_items

Fail if list length < `min_length`.

### cross_field_not_equal

Fail if `data[field] == data[other_field]`.

---

## 8.5 Quality report semantics

```text
passed = error_count == 0

warning_count does not fail report

review_count does not fail report by default, but can make conversion status review_required when options["quality_review_required"] = true
```

## 8.6 Acceptance criteria

```text
[ ] QualityRuleService validates non_empty.
[ ] QualityRuleService validates date_format and datetime_format.
[ ] QualityRuleService validates text_min_length.
[ ] QualityRuleService validates regex_match.
[ ] QualityRuleService validates enum_allowed.
[ ] QualityRuleService validates number_range.
[ ] QualityRuleService validates url_like.
[ ] QualityRuleService validates array_min_items.
[ ] QualityRuleService validates cross_field_not_equal.
[ ] Tests cover pass, warning, review, and error severities.
```

---

# 9. Task 3.5: Load Quality Rules from SchemaPack

## 9.1 Files to modify

```text
backend/app/services/schema_pack_service.py
scripts/validate_schema_pack.py
```

## 9.2 Required methods

Add to `SchemaPackService`:

```python
def load_quality_rules(self, schema_pack_id: str) -> dict[str, Any]:
    return self.load_yaml_asset(schema_pack_id, "quality_rules.yaml")
```

If the current YAML reader cannot parse nested quality rules reliably, implement a better minimal YAML reader or add PyYAML only if dependency policy allows.

Recommended safe path:

```text
Use existing limited YAML reader only if it supports list of objects.
If not, add a local parser specifically for this supported format.
Do not silently ignore unparsed nested fields.
```

## 9.3 Validator updates

`validate_schema_pack.py` must check:

```text
schema_pack.yaml exists
quality_rules.yaml exists
schema_pack.yaml asset references exist
quality_rules.schema_id matches target_schema.schema_id
quality rule IDs are unique
each quality rule field exists in target schema fields or metadata_template fields
rule type is supported
severity is one of error/warning/review
regex patterns compile
date/datetime format strings are valid enough to test with sample values or at least non-empty
```

## 9.4 Acceptance criteria

```text
[ ] SchemaPack validator validates quality_rules.yaml.
[ ] Invalid quality rule field causes failed validation.
[ ] Invalid rule type causes failed validation.
[ ] Invalid regex pattern causes failed validation.
[ ] Duplicate rule_id causes failed validation.
```

---

# 10. Task 3.6: Integrate Quality Rules into Topic5ConversionService

## 10.1 Files to modify

```text
backend/app/schemas/topic5_convert.py
backend/app/services/topic5_conversion_service.py
backend/app/services/task_execution_service.py
backend/app/services/package_service.py
backend/tests/test_topic5_quality_rules_integration.py
```

## 10.2 Request model update

Add optional inline quality rules:

```python
quality_rules: QualityRulesConfig | None = None
```

In `Topic5ConvertRequest`:

```python
quality_rules: QualityRulesConfig | None = None
```

Public input concept:

```text
quality_rules is optional in Topic 5 input.
If absent, conversion still runs.
If present, quality_report is generated.
```

## 10.3 Response model update

Add:

```python
quality_report: dict[str, Any] | None = None
```

## 10.4 Conversion flow

After final `validation_report` is generated and before package creation:

```python
quality_report = None

if request.quality_rules is not None:
    quality_report_model = QualityRuleService().validate(
        task_id=task_id,
        schema_id=schema.schema_id,
        content_json=rendered.structured_json,
        rules_config=request.quality_rules,
    )
    quality_report = quality_report_model.model_dump(mode="json")
```

## 10.5 Status integration

Update `_final_status` or final status logic:

```text
If quality_report.error_count > 0:
  status = review_required or failed?
```

Recommended for coursework:

```text
quality errors -> review_required
package verifier failure -> failed
```

Reason: quality failures indicate output needs review or correction, not system crash.

If `options["strict_quality"] == true`:

```text
quality errors -> failed
```

If `options["quality_review_required"] == true` and review_count > 0:

```text
status = review_required
```

## 10.6 TaskExecutionService integration

For registered SchemaPack task execution:

1. Load quality rules from SchemaPack if file exists.
2. Run quality validation.
3. Write report path:

```text
quality_report.json
```

4. Add to execution snapshot:

```json
"quality_report": "tasks/<task_id>/quality_report.json"
```

Do not break tasks if no quality rules exist. Missing quality rules should produce:

```text
quality_report = null
```

or a report with:

```json
{
  "enabled": false
}
```

## 10.7 PackageService integration

Do not break Package 1.1 verifier.

Recommended default:

```text
quality_report is a task report, not a required package artifact.
```

Optional package inclusion:

```text
options.include_quality_report_in_package = true
```

If included:

```text
- add quality_report.json to package files
- manifest role = quality_report
- required = false
```

Do not make it required in Package 1.1.

## 10.8 Acceptance criteria

```text
[ ] Inline Topic5 request can include quality_rules.
[ ] Response includes quality_report when quality_rules are supplied.
[ ] Quality errors make status review_required by default.
[ ] strict_quality can make quality errors failed if implemented.
[ ] Existing conversion works without quality_rules.
[ ] Package verifier remains backward compatible.
```

---

# 11. Task 3.7: SchemaPack Quality Evaluation Script

## 11.1 File to create

```text
scripts/eval_schema_pack_quality.py
```

## 11.2 CLI

```powershell
python scripts/eval_schema_pack_quality.py `
  --schema-pack schema_packs/examples/announcement_doc `
  --out reports/schema_pack_quality_announcement_doc.json `
  --markdown reports/schema_pack_quality_announcement_doc.md
```

Also support all examples:

```powershell
python scripts/eval_schema_pack_quality.py `
  --all-examples `
  --out reports/schema_pack_quality_all.json `
  --markdown reports/schema_pack_quality_all.md
```

## 11.3 Required behavior

For each SchemaPack:

1. Validate SchemaPack contract.
2. Load example UIR/request if available.
3. Run Topic5 conversion with quality_rules.
4. Generate quality_report.
5. Count quality errors/warnings/reviews.
6. Run negative badcases if present.
7. Return pass/fail.

## 11.4 Report format

```json
{
  "status": "passed",
  "total_schema_packs": 2,
  "passed_schema_packs": 2,
  "failed_schema_packs": 0,
  "items": [
    {
      "schema_pack_id": "announcement_doc",
      "contract_valid": true,
      "conversion_passed": true,
      "quality_passed": true,
      "error_count": 0,
      "warning_count": 0,
      "review_count": 0,
      "badcase_violations": 0
    }
  ]
}
```

Markdown:

```markdown
# SchemaPack Quality Evaluation

- status: passed
- total schema packs: 2
- passed: 2
- failed: 0

| SchemaPack | Contract | Conversion | Quality | Errors | Warnings | Reviews |
| --- | --- | --- | --- | ---: | ---: | ---: |
| announcement_doc | passed | passed | passed | 0 | 0 | 0 |
```

## 11.5 Acceptance criteria

```text
[ ] eval_schema_pack_quality.py exists.
[ ] It can run one SchemaPack.
[ ] It can run all examples.
[ ] It writes JSON and Markdown reports.
[ ] It fails when quality rules fail with error severity.
```

---

# 12. Task 3.8: Add Badcase Regression to SchemaPack

## 12.1 Files to create

```text
schema_packs/examples/announcement_doc/badcases/negative_pairs.jsonl
schema_packs/examples/event_notice_doc/badcases/negative_pairs.jsonl
schema_packs/examples/event_notice_doc/badcases/event_badcase_001_uir.json
schema_packs/examples/announcement_doc/badcases/announcement_badcase_001_uir.json
```

## 12.2 Badcase examples

Announcement:

```text
retrieved_at must not map to publish_date
page capture time must not map to publish_date
```

Event notice:

```text
publish date must not map to event_time
retrieved_at must not map to event_time
```

## 12.3 Acceptance criteria

```text
[ ] Badcases are stored inside each SchemaPack.
[ ] eval_schema_pack_quality.py checks them.
[ ] badcase violations = 0.
```

---

# 13. Task 3.9: Documentation Updates

## 13.1 Files to create or update

```text
docs/schema_pack_quality_contract.md
docs/schema_pack_onboarding_checklist.md
docs/topic5_convert_api.md
docs/mapping_rules_contract.md
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
```

## 13.2 Required content for `docs/schema_pack_quality_contract.md`

```text
# SchemaPack Quality Contract

## 1. Purpose
## 2. SchemaPack Manifest
## 3. Quality Rules File
## 4. Supported Rule Types
## 5. Severity Semantics
## 6. Quality Report
## 7. Package Compatibility
## 8. Badcase Regression
## 9. Examples
## 10. Non-goals
```

## 13.3 Required positioning

Use this wording:

```text
SchemaPack is a reusable external configuration contract that defines target schema, metadata template, mapping rules, content organization parameters, optional router rules, and quality rules.
```

Use this boundary:

```text
SchemaPack examples are reusable configuration assets and evaluation baselines, not system capability boundaries.
```

## 13.4 Quality rules boundary

Include:

```text
Quality rules validate the converted structured output. They do not parse raw source documents and do not replace schema validation.
```

## 13.5 Acceptance criteria

```text
[ ] Documentation explains schema_pack.yaml.
[ ] Documentation explains quality_rules.yaml.
[ ] Documentation explains quality_report.json.
[ ] Documentation explains status impact.
[ ] Documentation avoids production overclaim.
```

---

# 14. Task 3.10: Tests

## 14.1 Required test files

```text
backend/tests/test_quality_rule_service.py
backend/tests/test_topic5_quality_rules_integration.py
backend/tests/test_schema_pack_quality_eval.py
backend/tests/test_schema_pack_contract_validation.py
```

## 14.2 Required test cases

### QualityRuleService

```text
non_empty passes and fails
date_format passes and fails
datetime_format passes and fails
text_min_length warning
regex_match passes and fails
enum_allowed passes and fails
number_range passes and fails
url_like optional missing passes
array_min_items passes and fails
cross_field_not_equal passes and fails
```

### Topic5 integration

```text
inline conversion without quality_rules remains completed
inline conversion with passing quality_rules returns quality_report.passed = true
inline conversion with error quality rule returns review_required
inline conversion with warning quality rule keeps completed but includes warning
```

### SchemaPack validation

```text
announcement_doc validates
event_notice_doc validates
missing quality_rules.yaml fails or warns according to selected policy
duplicate quality rule id fails
invalid quality rule field fails
invalid rule type fails
invalid regex fails
```

### Quality eval script

```text
single SchemaPack eval passes
all examples eval passes
badcase violation fails
quality error fails
```

---

# 15. Final Verification Commands

Run all from repository root.

```powershell
# Carry-over fixes and validators
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc
python scripts/validate_schema_pack.py schema_packs/examples/event_notice_doc

# SchemaPack quality eval
python scripts/eval_schema_pack_quality.py `
  --all-examples `
  --out reports/schema_pack_quality_all.json `
  --markdown reports/schema_pack_quality_all.md

# Topic5 inline demos
python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/announcement_convert_request.json `
  --out reports/topic5_inline_announcement_result.json `
  --create-package

python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/event_notice_convert_request.json `
  --out reports/topic5_inline_event_notice_result.json `
  --create-package

# Phase 2 mapping gate, regenerated with corrected package verifier metrics
python scripts/check_topic5_mapping_quality_gate.py `
  --mode global_assignment

# Topic 5 alignment gate
python scripts/check_topic5_alignment_gate.py

# Full verification
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Optional:

```powershell
Push-Location frontend
npm.cmd test
Pop-Location
```

---

# 16. Required Reports

Generate or update:

```text
reports/schema_pack_quality_all.json
reports/schema_pack_quality_all.md
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
reports/topic5_inline_announcement_result.json
reports/topic5_inline_event_notice_result.json
reports/topic5_alignment_gate_report.json
reports/topic5_alignment_gate_report.md
docs/openapi.json
```

---

# 17. Phase 3 Acceptance Gate

Phase 3 is complete only if:

```text
[ ] Carry-over fixes from Phase 2 are complete.
[ ] schema_pack.yaml exists for at least announcement_doc and event_notice_doc.
[ ] quality_rules.yaml exists for at least announcement_doc and event_notice_doc.
[ ] SchemaPack validator validates manifest and quality rules.
[ ] QualityRuleService exists and has unit tests.
[ ] Topic5 inline conversion supports optional quality_rules.
[ ] quality_report is generated when quality_rules are present.
[ ] Quality errors affect status as specified.
[ ] Existing conversions still work without quality_rules.
[ ] SchemaPack quality evaluation script exists.
[ ] SchemaPack quality eval passes for all example packs.
[ ] Badcase regression is checked.
[ ] Package 1.1 compatibility is preserved.
[ ] Documentation is updated.
[ ] Full verification passes.
```

---

# 18. Recommended Success Statement

Use this statement after Phase 3 passes:

```text
Phase 3 upgrades SchemaPack from example configuration files into a reusable quality-governed configuration contract. Each SchemaPack can declare target schema, metadata template, mapping rules, content organization parameters, router hints, quality rules, examples, tests, and badcases. The conversion pipeline can generate a quality_report and use it to mark outputs as completed, review_required, or failed according to configured severity. Package 1.1 compatibility is preserved, while optional quality artifacts prepare the project for a future Package 1.2 contract.
```

---

# 19. Do Not Do in Phase 3

Do not:

```text
- make quality_report required in existing Package 1.1
- add LLM rule generation
- auto-fix data using quality rules without explicit governance
- hide per-schema weak metrics behind aggregate pass
- claim production-grade quality monitoring
- break legacy conversions with no quality_rules
- hardcode quality rules in backend services
```
