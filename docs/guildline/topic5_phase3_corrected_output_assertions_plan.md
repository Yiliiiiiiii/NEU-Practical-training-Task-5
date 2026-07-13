# Phase 3 Execution Plan: SchemaPack Contract and Conversion Output Assertions

Version: 2.0  
Language: English  
Recommended target branch: `feat/schema-pack-output-assertions`  
Recommended base branch: the accepted Phase 2 branch, usually `feat/topic5-mapping-benchmark` after review  
Primary objective: strengthen SchemaPack as a reusable Topic 5 configuration contract without crossing into Topic 6 quality inspection.

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

# 

## 0. Mandatory Boundary Correction

This phase was previously named:

```text
SchemaPack Contract and Quality Rules
```

That wording is risky because Topic 6 in the task book is the independent **Data Quality Inspection Agent**, responsible for quality scoring, quality grades, defect reports, and route suggestions.

The corrected Phase 3 name is:

```text
SchemaPack Contract and Conversion Output Assertions
```

In this phase, **do not build a Topic 6 quality inspection agent**.

The intended scope is:

```text
SchemaPack-scoped conversion output assertions
+ field-level output constraints
+ package/artifact existence assertions
+ chunk/source-link assertions
+ badcase regression assertions
+ assertion report generation
```

The forbidden scope is:

```text
quality scoring
quality grading
route suggestions
publish/reject decisions
final quality inspection
process quality gates
semantic fidelity evaluation
LLM-as-Judge evaluation
over-cleaning detection
readability scoring
human-score correlation
```

Use this boundary statement in all new documents:

```text
Conversion output assertions in this phase are SchemaPack-scoped checks for Topic 5 conversion outputs. They validate field-level, chunk-level, and package-level correctness after conversion. They are not a Topic 6 quality inspection agent, and they do not provide quality scores, quality grades, routing recommendations, semantic fidelity evaluation, or LLM-as-Judge assessment.
```

---

## 1. Phase 3 Goal

Phase 0 and Phase 1 corrected the Topic 5 input/output contract:

```text
UIR
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
-> Standard Topic 5 conversion package
```

Phase 2 added measurable automatic mapping improvement:

```text
standard UIR benchmark
+ dev/test/blind splits
+ global assignment mapper
+ mapping quality gate
+ badcase regression
```

Phase 3 now upgrades SchemaPack from a folder of example files into a reusable, versioned, testable contract.

After Phase 3, a SchemaPack should be able to declare:

```text
1. what target schema it supports
2. what metadata template it expects
3. how mapping rules are applied
4. how content organization should behave
5. what output assertions must hold after conversion
6. what examples and badcases verify the pack
7. what compatibility boundary the pack claims
```

The phase output should include:

```text
schema_pack.yaml
conversion_output_assertions.yaml
conversion_output_assertion_report.json
SchemaPack contract validator
SchemaPack assertion evaluator
badcase regression report
updated handoff documentation
```

---

## 2. Task-Book Alignment

This phase supports Topic 5 requirements in the following way:

| Topic 5 requirement | Phase 3 support |
| --- | --- |
| Input includes target Schema / metadata template / mapping rules / content organization parameters | `schema_pack.yaml` formally binds these assets |
| Schema validation must be complete | output assertions complement existing schema validation |
| Field operation accuracy must be measurable | assertion rules check normalized output values and transformation effects |
| Double-form package must be complete | package/artifact assertions verify expected outputs exist |
| Chunks must contain tags/entities/summary/source links | chunk-level assertions verify required chunk metadata |
| Output must be directly consumable | downstream artifact assertions can check export-ready fields |
| Reproducibility and badcase analysis | SchemaPack examples, tests, and badcases are evaluated by scripts |

This phase intentionally does **not** implement Topic 6 requirements such as:

```text
quality score
quality level
routing recommendation
full final inspection report
semantic fidelity scoring
LLM judge consistency
defect-location scoring
```

---

## 3. Carry-over Fixes from Phase 2

Before adding new Phase 3 features, apply the following carry-over fixes. These fixes are part of this execution plan.

---

### 3.1 Fix `validate_schema_pack.py` negative-pair regex handling

#### Problem

The validator currently may compile negative-pair regex patterns in a way that can crash on invalid regex instead of returning a normal validation error.

#### File to modify

```text
scripts/validate_schema_pack.py
```

#### Required implementation

Find the negative-pair regex validation logic and replace it with explicit exception handling:

```python
try:
    re.compile(str(item["source_pattern"]))
except re.error as exc:
    errors.append(
        f"negative_pairs[{index}].source_pattern is invalid: {exc}"
    )
```

#### Required test

File:

```text
backend/tests/test_schema_pack_contract_validation.py
```

Add:

```python
def test_validate_schema_pack_reports_invalid_negative_pair_regex(tmp_path):
    pack_dir = make_schema_pack_copy(tmp_path, "announcement_doc")
    negative_pairs_path = pack_dir / "mapping_rules.yaml"

    # Modify or create a negative pair with invalid regex source_pattern = "["
    # Run validator
    result = validate_schema_pack(pack_dir)

    assert result["status"] == "failed"
    assert any("source_pattern is invalid" in item for item in result["errors"])
```

#### Acceptance criteria

```text
[ ] Invalid regex does not crash the script.
[ ] Invalid regex is reported as a validation error.
[ ] Valid packs still pass.
```

---

### 3.2 Rename misleading evaluator package metric

#### Problem

The Phase 2 evaluator may use a field named `package_pass_rate` even when packages are not actually created and verified. This is misleading.

#### Files to modify

```text
scripts/eval_topic5_standard_uir_mapping.py
scripts/check_topic5_mapping_quality_gate.py
backend/tests/test_topic5_standard_uir_eval.py
reports/topic5_standard_uir_*.json
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
```

#### Required metric names

Use:

```text
conversion_pass_rate
package_verifier_pass_rate
package_verified_count
```

Do not use:

```text
package_pass_rate
```

unless it means actual package verifier success.

#### Required CLI behavior

Add:

```text
--verify-package
```

Default:

```text
false
```

Final gate reports should run with:

```text
--verify-package
```

#### Required implementation idea

```python
response = Topic5ConversionService(tmp_dir).convert(
    request,
    create_package=args.verify_package,
)

conversion_passed = response.status in {"completed", "review_required"}

if args.verify_package:
    package_verified_count += 1
    if response.verifier_report and response.verifier_report.get("passed") is True:
        package_verifier_passed_count += 1
```

Aggregate:

```python
conversion_pass_rate = conversion_passed_count / max(total_count, 1)

package_verifier_pass_rate = (
    package_verifier_passed_count / package_verified_count
    if package_verified_count else None
)
```

#### Acceptance criteria

```text
[ ] Fast benchmark runs can skip package verification.
[ ] Final gate can verify packages explicitly.
[ ] Reports distinguish conversion success from package verifier success.
```

---

### 3.3 Add per-schema warning section to mapping quality gate

#### Problem

Aggregate mapping metrics can hide weak schema families.

#### Files to modify

```text
scripts/check_topic5_mapping_quality_gate.py
scripts/eval_topic5_standard_uir_mapping.py
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
docs/交接/topic5_mapping_quality_phase2.md
```

#### Required thresholds

Hard fail:

```text
aggregate auto_precision >= 0.90
aggregate auto_recall >= 0.85
aggregate required_missing = 0
aggregate badcase_violations = 0
```

Phase 3 warning only:

```text
per_schema_auto_precision < 0.85
per_schema_auto_recall < 0.85
```

Hard fail:

```text
per_schema_required_missing > 0
per_schema_badcase_violations > 0
```

#### Required report structure

```json
{
  "status": "passed",
  "failed_checks": [],
  "warnings": [
    {
      "type": "schema_precision_below_recommended_threshold",
      "schema_id": "policy_doc",
      "actual": 0.80,
      "threshold": 0.85
    }
  ]
}
```

#### Acceptance criteria

```text
[ ] Per-schema weak spots are visible.
[ ] Aggregate pass does not hide required-missing or badcase failures.
[ ] Precision/recall per-schema weaknesses are warnings in Phase 3.
```

---

### 3.4 Tighten MappingRepairService auto-accept logic

#### Problem

A repair candidate above review threshold may be auto-accepted. That is too permissive.

#### Files to modify

```text
backend/app/services/mapping_repair_service.py
backend/tests/test_mapping_repair_service.py
```

#### Required behavior

Use two thresholds:

```text
repair_auto_accept_threshold = 0.82
repair_review_threshold = 0.62
```

Behavior:

```text
score >= repair_auto_accept_threshold:
  accepted repair mapping

repair_review_threshold <= score < repair_auto_accept_threshold:
  review_required repair item

score < repair_review_threshold:
  remains unmapped
```

Do not auto-accept negative-pair candidates.

#### Required report fields

```json
{
  "accepted_repair_fields": [],
  "review_repair_fields": [],
  "unrepaired_fields": [],
  "blocked_candidates": []
}
```

#### Acceptance criteria

```text
[ ] Low-confidence repair is not accepted.
[ ] Review-range repair becomes review_required.
[ ] Negative-pair repair candidate is blocked.
```

---

### 3.5 Update Phase 2 claim boundary

#### Files to modify

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/topic5_mapping_quality_phase2.md
reports/topic5_mapping_quality_gate_report.md
```

#### Required wording

Use:

```text
The project can claim Topic 5 benchmark-level automatic mapping recall >= 0.85 within the declared standard UIR benchmark scope. This is not a production shadow/blind claim and not an arbitrary-schema production claim.
```

Forbidden overclaim phrases:

```text
production-grade auto mapping
arbitrary-schema 0.85
production blind recall passed
universal schema matching
```

#### Acceptance criteria

```text
[ ] Documentation uses benchmark-level claim wording.
[ ] No production-grade claim remains.
```

---

## 4. Phase 3 Scope

### 4.1 In scope

```text
schema_pack.yaml manifest
conversion_output_assertions.yaml contract
ConversionOutputAssertionService
conversion_output_assertion_report.json
SchemaPack validator extension
SchemaPack assertion evaluator script
SchemaPack examples/tests/badcases structure
optional package inclusion as non-required artifact
documentation and tests
```

### 4.2 Out of scope

```text
quality scoring
quality grading
route suggestion
publishing decision
final quality inspection
process quality inspection
semantic fidelity comparison
LLM-as-Judge
readability scoring
over-cleaning detection
topic 6 quality inspection agent
topic 12 content fidelity evaluator
full topic 11 retrieval metric loop
```

### 4.3 Naming rule

Use preferred terms:

```text
conversion output assertion
output assertion
assertion report
SchemaPack contract
field constraint
artifact assertion
chunk source-link assertion
badcase regression
```

Avoid or restrict terms:

```text
quality score
quality grade
quality routing
inspection
final check
semantic fidelity
LLM judge
```

If `quality` appears in existing historical documents, clarify that it refers only to field-level output constraints and not Topic 6 quality inspection.

---

## 5. Recommended Branching

```powershell
git checkout feat/topic5-mapping-benchmark
git pull
git checkout -b feat/schema-pack-output-assertions
```

Recommended commit sequence:

```text
fix: harden phase2 evidence metrics
feat: add schema pack manifest contract
feat: add conversion output assertions
feat: add schema pack assertion evaluator
docs: document phase3 topic5 assertion boundary
```

Do not mix Phase 4 dual-form consistency work into this branch unless explicitly requested.

---

## 6. Target SchemaPack Directory Structure

Each SchemaPack should support:

```text
schema_packs/examples/<schema_pack_id>/
  schema_pack.yaml
  target_schema.json
  metadata_template.json
  mapping_rules.yaml
  content_org.yaml
  conversion_output_assertions.yaml
  router_rules.yaml
  examples/
    example_001_uir.json
    example_001_request.json
    expected_content.json
  tests/
    expected_mapping.json
    expected_assertions.json
  badcases/
    negative_pairs.jsonl
    badcase_001_uir.json
```

Minimum Phase 3 requirement:

```text
announcement_doc and event_notice_doc must have the full structure.
Historical packs may have minimal schema_pack.yaml if time is limited.
```

---

## 7. Task 3.1: Add `schema_pack.yaml`

### 7.1 Files to create

```text
schema_packs/examples/announcement_doc/schema_pack.yaml
schema_packs/examples/event_notice_doc/schema_pack.yaml
```

### 7.2 Required manifest format

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
  assertion_contract: "1.0"

assets:
  target_schema: target_schema.json
  metadata_template: metadata_template.json
  mapping_rules: mapping_rules.yaml
  content_org: content_org.yaml
  conversion_output_assertions: conversion_output_assertions.yaml
  router_rules: router_rules.yaml

supported_input:
  uir_version: "1.0"
  languages:
    - zh-CN
    - en-US
  source_formats:
    - standard_uir

assertion_policy:
  fail_on_error: false
  review_on_error: true
  review_on_review: true
  include_assertion_report_in_package: false

claim_boundary:
  description: Example configuration and benchmark baseline, not system capability boundary.
  production_ready: false
  topic_boundary: "Topic 5 conversion output assertions only; not Topic 6 quality inspection."
```

### 7.3 Field semantics

```text
schema_pack_id:
  stable identifier

schema_pack_version:
  semver-like version

runtime.package_contract:
  current package contract; keep 1.1 unless package format changes

runtime.assertion_contract:
  conversion output assertion contract version

assets.conversion_output_assertions:
  path to SchemaPack output assertion file

assertion_policy.fail_on_error:
  if true, assertion error can make conversion status failed.
  default false for coursework safety.

assertion_policy.review_on_error:
  if true, assertion error makes conversion status review_required.

assertion_policy.review_on_review:
  if true, review-severity assertion issue makes conversion status review_required.

claim_boundary.topic_boundary:
  required line preventing Topic 6 scope drift.
```

### 7.4 Acceptance criteria

```text
[ ] schema_pack.yaml exists for announcement_doc.
[ ] schema_pack.yaml exists for event_notice_doc.
[ ] asset paths point to existing files.
[ ] topic_boundary explicitly says not Topic 6.
```

---

## 8. Task 3.2: Extend SchemaPack Contract Schema

### 8.1 File to modify

```text
schema_packs/schema_pack_contract.schema.json
```

### 8.2 Required additions

Add schema definitions for:

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
assertion_policy
claim_boundary
```

Add `conversion_output_assertions` asset as optional in contract v1.0 but required for example packs that opt into assertions.

### 8.3 Required validation rules

```text
schema_pack_id must match target_schema.schema_id.
assets.target_schema must exist.
assets.metadata_template must exist.
assets.mapping_rules must exist.
assets.content_org must exist.
assets.conversion_output_assertions must exist if declared.
claim_boundary.topic_boundary must contain "not Topic 6" or equivalent.
```

### 8.4 Acceptance criteria

```text
[ ] Contract schema documents schema_pack.yaml.
[ ] Validator can validate manifest structure.
[ ] Boundary field is enforced or warned.
```

---

## 9. Task 3.3: Add `conversion_output_assertions.yaml`

### 9.1 Files to create

```text
schema_packs/examples/announcement_doc/conversion_output_assertions.yaml
schema_packs/examples/event_notice_doc/conversion_output_assertions.yaml
```

### 9.2 Contract format

Announcement example:

```yaml
schema_id: announcement_doc
version: 1.0.0
description: Field-level and artifact-level assertions for Topic 5 announcement conversion output.

assertions:
  - assertion_id: title_non_empty
    scope: field
    field: title
    assertion: non_empty
    severity: error
    message: Converted title must not be empty.

  - assertion_id: publish_date_format
    scope: field
    field: publish_date
    assertion: date_format
    severity: error
    format: "%Y-%m-%d"
    optional: true
    message: Publish date must be normalized to YYYY-MM-DD when present.

  - assertion_id: body_min_length
    scope: field
    field: body
    assertion: text_min_length
    severity: warning
    min_length: 10
    message: Body is unusually short.

  - assertion_id: chunks_have_source_links
    scope: chunk
    assertion: chunk_source_link_present
    severity: error
    message: Every chunk must keep a source link.

  - assertion_id: required_package_artifacts
    scope: artifact
    assertion: required_artifacts_present
    severity: error
    required_artifacts:
      - content.json
      - content.md
      - chunks.json
      - manifest.json
    message: Standard Topic 5 package artifacts must exist.
```

Event notice example:

```yaml
schema_id: event_notice_doc
version: 1.0.0
description: Field-level and chunk-level assertions for event notice conversion output.

assertions:
  - assertion_id: title_non_empty
    scope: field
    field: title
    assertion: non_empty
    severity: error

  - assertion_id: organizer_non_empty
    scope: field
    field: organizer
    assertion: non_empty
    severity: error

  - assertion_id: event_time_datetime
    scope: field
    field: event_time
    assertion: datetime_format
    severity: error
    formats:
      - "%Y-%m-%d %H:%M"
      - "%Y-%m-%dT%H:%M:%S"

  - assertion_id: publish_date_not_event_time
    scope: field
    field: event_time
    assertion: regex_not_match
    severity: error
    pattern: "发布时间|发布日期|抓取时间|retrieved_at"
    message: Event time must not be derived from publish or retrieved time labels.

  - assertion_id: body_min_length
    scope: field
    field: body
    assertion: text_min_length
    severity: warning
    min_length: 10

  - assertion_id: chunks_have_tags
    scope: chunk
    assertion: chunk_tags_present
    severity: warning
```

### 9.3 Supported scopes

```text
field:
  assertion checks one field in content_json.data or metadata

metadata:
  assertion checks document-level metadata

chunk:
  assertion checks chunks and chunk metadata

artifact:
  assertion checks package/report artifact existence and manifest references
```

### 9.4 Supported severities

```text
error:
  assertion_report.passed = false
  conversion status becomes review_required by default

warning:
  assertion_report.passed can remain true
  conversion status unchanged

review:
  assertion_report.passed can remain true
  conversion status becomes review_required if review_on_review is enabled
```

Do not implement scoring or grading.

### 9.5 Phase 3 supported assertion types

Implement these first:

```text
non_empty
date_format
datetime_format
text_min_length
regex_match
regex_not_match
enum_allowed
number_range
array_min_items
cross_field_not_equal
chunk_source_link_present
chunk_tags_present
required_artifacts_present
manifest_artifact_checksum_present
```

Optional later:

```text
url_like
email_like
phone_like
not_future
required_if
metadata_key_present
```

Do not implement semantic fidelity, readability, or LLM judge assertions.

### 9.6 Acceptance criteria

```text
[ ] conversion_output_assertions.yaml exists for announcement_doc.
[ ] conversion_output_assertions.yaml exists for event_notice_doc.
[ ] It uses "assertions", not "quality_rules".
[ ] It includes a statement or docs clarifying Topic 5-only scope.
```

---

## 10. Task 3.4: Add Pydantic Schemas for Output Assertions

### 10.1 Files to add

```text
backend/app/schemas/conversion_output_assertions.py
```

### 10.2 Required models

```python
from typing import Any, Literal
from pydantic import Field
from app.schemas.base import StrictBaseModel


AssertionScope = Literal["field", "metadata", "chunk", "artifact"]
AssertionSeverity = Literal["error", "warning", "review"]


class ConversionOutputAssertion(StrictBaseModel):
    assertion_id: str
    scope: AssertionScope
    assertion: str
    severity: AssertionSeverity = "error"

    field: str | None = None
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
    required_artifacts: list[str] = Field(default_factory=list)


class ConversionOutputAssertionsConfig(StrictBaseModel):
    schema_id: str
    version: str = "1.0.0"
    description: str | None = None
    assertions: list[ConversionOutputAssertion] = Field(default_factory=list)


class ConversionOutputAssertionIssue(StrictBaseModel):
    assertion_id: str
    scope: str
    assertion: str
    severity: str
    field: str | None = None
    message: str
    value_preview: str | None = None
    source_path: str | None = None


class ConversionOutputAssertionReport(StrictBaseModel):
    task_id: str
    schema_id: str
    passed: bool
    error_count: int
    warning_count: int
    review_count: int
    issues: list[ConversionOutputAssertionIssue] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
```

### 10.3 Acceptance criteria

```text
[ ] Models are strict.
[ ] The report has no score or grade field.
[ ] The report has issue counts and issue details only.
```

---

## 11. Task 3.5: Implement ConversionOutputAssertionService

### 11.1 Files to add

```text
backend/app/services/conversion_output_assertion_service.py
backend/tests/test_conversion_output_assertion_service.py
```

### 11.2 Service signature

```python
class ConversionOutputAssertionService:
    def evaluate(
        self,
        *,
        task_id: str,
        schema_id: str,
        content_json: dict[str, Any],
        chunks: list[dict[str, Any]] | None,
        manifest: dict[str, Any] | None,
        config: ConversionOutputAssertionsConfig,
    ) -> ConversionOutputAssertionReport:
        ...
```

### 11.3 Field lookup order

For `scope=field`:

```text
content_json["data"][field]
content_json["metadata"][field]
content_json[field]
None
```

For `scope=metadata`:

```text
content_json["metadata"][field]
None
```

For `scope=chunk`:

```text
iterate chunks
```

For `scope=artifact`:

```text
check manifest and available artifact names
```

### 11.4 Assertion behavior

#### non_empty

Fail if value is:

```text
None
""
[]
{}
```

#### date_format

Default format:

```text
%Y-%m-%d
```

Use `datetime.strptime`.

#### datetime_format

Try all provided `formats`. If absent, default:

```text
%Y-%m-%d %H:%M
%Y-%m-%dT%H:%M:%S
%Y-%m-%dT%H:%M:%S%z
```

#### text_min_length

Convert value to string and check `len(value) >= min_length`.

#### regex_match

Compile and match pattern against string value.

#### regex_not_match

Fail if pattern matches string value.

#### enum_allowed

Fail if value not in `allowed_values`.

#### number_range

Convert value to number and check:

```text
min_value <= value <= max_value
```

Only enforce bounds that are provided.

#### array_min_items

Fail if value is not a list or length < `min_length`.

#### cross_field_not_equal

Fail if:

```text
data[field] == data[other_field]
```

#### chunk_source_link_present

Every chunk must have at least one of:

```text
source_path
source_block_id
source_blocks
source_anchor
origin
```

Use the actual chunk schema fields in the project.

#### chunk_tags_present

Every chunk must have at least one non-empty tag field:

```text
tags
content_tags
management_tags
entity_tags
```

#### required_artifacts_present

Check manifest/artifact list contains all required artifact names.

#### manifest_artifact_checksum_present

Each artifact entry in manifest must contain a checksum field such as:

```text
sha256
checksum
```

Use actual manifest schema if available.

### 11.5 Report semantics

```python
passed = error_count == 0
```

Warnings do not fail `passed`.

Reviews do not fail `passed` by default, but can affect conversion status according to assertion policy.

### 11.6 No scoring

Do not add:

```text
score
quality_score
grade
level
route
route_suggestion
publish_decision
```

### 11.7 Tests

Required tests:

```text
non_empty pass/fail
date_format pass/fail
datetime_format pass/fail
text_min_length warning
regex_match pass/fail
regex_not_match pass/fail
enum_allowed pass/fail
number_range pass/fail
array_min_items pass/fail
cross_field_not_equal pass/fail
chunk_source_link_present pass/fail
chunk_tags_present warning
required_artifacts_present pass/fail
manifest_artifact_checksum_present pass/fail
```

### 11.8 Acceptance criteria

```text
[ ] Service evaluates field assertions.
[ ] Service evaluates chunk assertions.
[ ] Service evaluates artifact assertions.
[ ] Service returns report without quality score/grade/route.
[ ] All unit tests pass.
```

---

## 12. Task 3.6: Load Assertions from SchemaPack

### 12.1 Files to modify

```text
backend/app/services/schema_pack_service.py
scripts/validate_schema_pack.py
```

### 12.2 Required service method

Add:

```python
def load_conversion_output_assertions(
    self,
    schema_pack_id: str,
) -> ConversionOutputAssertionsConfig | None:
    ...
```

or if service currently returns dicts:

```python
def load_conversion_output_assertions(self, schema_pack_id: str) -> dict[str, Any] | None:
    ...
```

### 12.3 YAML parsing requirement

The parser must correctly support:

```text
list of assertion objects
nested fields
patterns containing regex
formats list
required_artifacts list
```

If the existing YAML reader cannot support this safely, use one of these approaches:

```text
Preferred:
  use PyYAML if already allowed in project dependencies.

Fallback:
  implement a small safe YAML loader for this supported file shape.

Forbidden:
  silently ignore nested assertion fields.
```

### 12.4 Validator updates

`validate_schema_pack.py` must validate:

```text
schema_pack.yaml exists
conversion_output_assertions.yaml exists when declared
assertions.schema_id matches target_schema.schema_id
assertion_id values are unique
assertion.scope is supported
assertion.severity is supported
assertion.assertion type is supported
field assertion field exists in target_schema fields or metadata template
regex patterns compile
date/datetime formats are non-empty strings
required_artifacts is non-empty for required_artifacts_present
claim_boundary.topic_boundary exists
```

### 12.5 Acceptance criteria

```text
[ ] SchemaPackService can load output assertions.
[ ] Validator validates output assertion files.
[ ] Invalid rule type fails.
[ ] Invalid field fails.
[ ] Duplicate assertion_id fails.
[ ] Invalid regex fails.
```

---

## 13. Task 3.7: Integrate Assertions into Topic5ConversionService

### 13.1 Files to modify

```text
backend/app/schemas/topic5_convert.py
backend/app/services/topic5_conversion_service.py
backend/app/services/task_execution_service.py
backend/app/services/package_service.py
backend/tests/test_topic5_output_assertions_integration.py
```

### 13.2 Request model update

Add optional inline field:

```python
output_assertions: ConversionOutputAssertionsConfig | None = None
```

If you need backward compatibility with any earlier local work that used `quality_rules`, support it only as deprecated alias:

```python
quality_rules: ConversionOutputAssertionsConfig | None = None
```

If both are provided and differ:

```text
return 422
```

But the preferred public API term must be:

```text
output_assertions
```

### 13.3 Response model update

Add:

```python
conversion_output_assertion_report: dict[str, Any] | None = None
```

Do not name this field `quality_report`.

### 13.4 Conversion flow

After rendering `content_json`, content markdown, and chunks, and after manifest is available if package mode is used:

```python
assertion_report = None

if request.output_assertions is not None:
    assertion_report_model = ConversionOutputAssertionService().evaluate(
        task_id=task_id,
        schema_id=schema.schema_id,
        content_json=rendered.structured_json,
        chunks=chunks,
        manifest=manifest_dict,
        config=request.output_assertions,
    )
    assertion_report = assertion_report_model.model_dump(mode="json")
```

If manifest does not exist yet before package creation, run field/chunk assertions first and artifact assertions after package manifest is created. Two acceptable designs:

```text
Design A:
  evaluate field/chunk assertions before package;
  evaluate artifact assertions after package;
  merge reports.

Design B:
  create an in-memory planned manifest before assertion evaluation;
  package verifier remains final authority.
```

Prefer Design A if package manifest currently only exists after package creation.

### 13.5 Status integration

Update final status semantics:

```text
Package verifier failed:
  failed

Mapping review exists:
  review_required

Required unmapped exists:
  review_required

Schema validation failed:
  review_required

Output assertion error exists:
  review_required by default

Output assertion review issue exists and review_on_review=true:
  review_required

Only warnings:
  status unchanged

strict_output_assertions=true and assertion error exists:
  failed
```

Do not call this a route decision.

### 13.6 Registered SchemaPack task integration

For registered SchemaPack execution:

1. Load SchemaPack manifest.
2. Load output assertions if declared.
3. Run assertions.
4. Write report:

```text
tasks/<task_id>/conversion_output_assertion_report.json
```

5. Include report path in execution snapshot:

```json
{
  "conversion_output_assertion_report": "tasks/<task_id>/conversion_output_assertion_report.json"
}
```

Missing assertion file should not break legacy tasks unless manifest explicitly requires it.

### 13.7 Package integration

Do not change Package 1.1 required artifacts.

Default:

```text
conversion_output_assertion_report.json is a task report, not required package artifact.
```

Optional:

```text
include_assertion_report_in_package = true
```

If included:

```text
- add it as optional artifact
- manifest role = conversion_output_assertion_report
- required = false
```

### 13.8 Acceptance criteria

```text
[ ] Inline API accepts output_assertions.
[ ] Response includes conversion_output_assertion_report.
[ ] Existing conversion still works without output_assertions.
[ ] Assertion errors make status review_required by default.
[ ] Warnings do not change completed status.
[ ] Package 1.1 verifier remains backward compatible.
```

---

## 14. Task 3.8: Add SchemaPack Assertion Evaluation Script

### 14.1 File to create

```text
scripts/eval_schema_pack_assertions.py
```

### 14.2 CLI

Run one SchemaPack:

```powershell
python scripts/eval_schema_pack_assertions.py `
  --schema-pack schema_packs/examples/announcement_doc `
  --out reports/schema_pack_assertions_announcement_doc.json `
  --markdown reports/schema_pack_assertions_announcement_doc.md
```

Run all example packs:

```powershell
python scripts/eval_schema_pack_assertions.py `
  --all-examples `
  --out reports/schema_pack_assertions_all.json `
  --markdown reports/schema_pack_assertions_all.md
```

### 14.3 Required behavior

For each SchemaPack:

1. Validate `schema_pack.yaml`.
2. Validate `target_schema.json`.
3. Validate `mapping_rules.yaml`.
4. Validate `content_org.yaml`.
5. Validate `conversion_output_assertions.yaml`.
6. Load example UIR/request.
7. Run Topic5 conversion with output assertions.
8. Collect assertion report.
9. Run badcase regression if available.
10. Write JSON and Markdown reports.

### 14.4 Report JSON format

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
      "conversion_status": "completed",
      "assertion_report_passed": true,
      "error_count": 0,
      "warning_count": 0,
      "review_count": 0,
      "badcase_violations": 0
    }
  ]
}
```

### 14.5 Markdown format

```markdown
# SchemaPack Conversion Output Assertion Evaluation

- status: passed
- total schema packs: 2
- passed: 2
- failed: 0

| SchemaPack | Contract | Conversion | Assertions | Errors | Warnings | Reviews | Badcases |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| announcement_doc | passed | completed | passed | 0 | 0 | 0 | 0 |
```

### 14.6 Acceptance criteria

```text
[ ] Script evaluates one SchemaPack.
[ ] Script evaluates all examples.
[ ] Script writes JSON and Markdown.
[ ] Script fails when assertion errors exist.
[ ] Script does not calculate quality score or route suggestion.
```

---

## 15. Task 3.9: Add SchemaPack Badcase Regression

### 15.1 Files to create

```text
schema_packs/examples/announcement_doc/badcases/negative_pairs.jsonl
schema_packs/examples/event_notice_doc/badcases/negative_pairs.jsonl
schema_packs/examples/announcement_doc/badcases/announcement_badcase_001_uir.json
schema_packs/examples/event_notice_doc/badcases/event_notice_badcase_001_uir.json
```

### 15.2 Required badcases

Announcement:

```text
retrieved_at must not map to publish_date
capture_time must not map to publish_date
page_generated_at must not map to publish_date
```

Event notice:

```text
publish_date must not map to event_time
retrieved_at must not map to event_time
announcement_date must not map to event_time
```

### 15.3 Badcase report requirement

The evaluator must report:

```json
{
  "badcase_violations": 0,
  "badcases": []
}
```

If violation occurs:

```json
{
  "badcase_violations": 1,
  "badcases": [
    {
      "schema_pack_id": "event_notice_doc",
      "target_field_id": "event_time",
      "source_path": "$.metadata.publish_date",
      "reason": "publish_date must not map to event_time"
    }
  ]
}
```

### 15.4 Acceptance criteria

```text
[ ] Badcases live inside SchemaPack folders.
[ ] Evaluator checks badcases.
[ ] Badcase violations fail assertion evaluation.
```

---

## 16. Task 3.10: Documentation Updates

### 16.1 Files to create

```text
docs/schema_pack_output_assertions_contract.md
```

### 16.2 Files to update

```text
README.md
docs/topic5_convert_api.md
docs/mapping_rules_contract.md
docs/schema_pack_onboarding_checklist.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
docs/交接/topic5_mapping_quality_phase2.md
```

### 16.3 Required document sections

`docs/schema_pack_output_assertions_contract.md` must contain:

```text
# SchemaPack Conversion Output Assertions Contract

## 1. Purpose
## 2. Topic 5 Boundary
## 3. Non-goals
## 4. schema_pack.yaml
## 5. conversion_output_assertions.yaml
## 6. Supported Assertion Scopes
## 7. Supported Assertion Types
## 8. Severity Semantics
## 9. Assertion Report
## 10. Package Compatibility
## 11. Badcase Regression
## 12. Example
## 13. Migration Notes from quality_rules
```

### 16.4 Required wording

Use exactly or very close:

```text
SchemaPack is a reusable external configuration contract that defines target schema, metadata template, mapping rules, content organization parameters, optional router hints, and conversion output assertions.
```

Use:

```text
Conversion output assertions validate the converted output of Topic 5. They complement Schema validation and package verification. They do not replace the independent Topic 6 data quality inspection agent.
```

Use:

```text
The assertion report contains pass/fail issue counts and evidence. It does not contain quality score, quality grade, route suggestion, or publish decision.
```

### 16.5 Forbidden documentation phrases

Do not use:

```text
quality score
quality grade
final inspection
route suggestion
publish decision
LLM judge
semantic fidelity
content fidelity
over-cleaning
```

unless explicitly saying these are out of scope.

### 16.6 Acceptance criteria

```text
[ ] Documentation explains output assertions.
[ ] Documentation explains Topic 5 boundary.
[ ] Documentation explicitly excludes Topic 6 functions.
[ ] Demo script remains focused on Topic 5 conversion.
```

---

## 17. Task 3.11: Alignment Gate Update

### 17.1 File to modify

```text
scripts/check_topic5_alignment_gate.py
```

### 17.2 Required checks

Add required file checks:

```text
docs/schema_pack_output_assertions_contract.md
schema_packs/examples/announcement_doc/schema_pack.yaml
schema_packs/examples/event_notice_doc/schema_pack.yaml
schema_packs/examples/announcement_doc/conversion_output_assertions.yaml
schema_packs/examples/event_notice_doc/conversion_output_assertions.yaml
scripts/eval_schema_pack_assertions.py
```

Add forbidden overreach phrase checks:

```python
FORBIDDEN_TOPIC6_OVERREACH = [
    "quality score",
    "quality grade",
    "route suggestion",
    "publish decision",
    "LLM-as-Judge",
    "semantic fidelity",
    "final inspection",
]
```

Allow them only in a clearly marked "Non-goals" section if the check is smart enough. If not, use more precise forbidden phrases such as:

```text
"outputs quality score"
"generates quality grade"
"produces route suggestion"
"uses LLM-as-Judge"
```

### 17.3 Required positive phrase checks

Require at least one document to contain:

```text
not a Topic 6 quality inspection agent
conversion output assertions
SchemaPack-scoped
```

### 17.4 Acceptance criteria

```text
[ ] Gate fails if Phase 3 drifts into Topic 6 wording.
[ ] Gate passes when docs contain correct boundary statement.
```

---

## 18. Task 3.12: Tests

### 18.1 Required test files

```text
backend/tests/test_conversion_output_assertion_service.py
backend/tests/test_topic5_output_assertions_integration.py
backend/tests/test_schema_pack_assertion_eval.py
backend/tests/test_schema_pack_contract_validation.py
backend/tests/test_topic5_alignment_gate_phase3.py
```

### 18.2 Required service tests

```text
non_empty
date_format
datetime_format
text_min_length
regex_match
regex_not_match
enum_allowed
number_range
array_min_items
cross_field_not_equal
chunk_source_link_present
chunk_tags_present
required_artifacts_present
manifest_artifact_checksum_present
```

### 18.3 Required integration tests

```text
inline conversion without output_assertions still completed
inline conversion with passing output_assertions completed
inline conversion with assertion warning remains completed
inline conversion with assertion error becomes review_required
strict_output_assertions=true can make assertion error failed
deprecated quality_rules alias is either rejected or mapped to output_assertions with warning
```

### 18.4 Required validator tests

```text
announcement_doc validates
event_notice_doc validates
duplicate assertion_id fails
invalid assertion type fails
invalid scope fails
invalid severity fails
invalid field fails
invalid regex fails
missing declared assertion file fails
```

### 18.5 Required evaluator tests

```text
single SchemaPack assertion eval passes
all example assertion eval passes
badcase violation fails
assertion error fails
report has no score/grade/route fields
```

### 18.6 Acceptance criteria

```text
[ ] All new tests pass.
[ ] Existing Phase 0/1/2 tests pass.
[ ] No Package 1.1 regression.
```

---

## 19. Final Verification Commands

Run from repository root.

### 19.1 Validate SchemaPacks

```powershell
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc
python scripts/validate_schema_pack.py schema_packs/examples/event_notice_doc
```

### 19.2 Evaluate SchemaPack assertions

```powershell
python scripts/eval_schema_pack_assertions.py `
  --all-examples `
  --out reports/schema_pack_assertions_all.json `
  --markdown reports/schema_pack_assertions_all.md
```

### 19.3 Re-run Topic5 inline demos

```powershell
python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/announcement_convert_request.json `
  --out reports/topic5_inline_announcement_result.json `
  --create-package

python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/event_notice_convert_request.json `
  --out reports/topic5_inline_event_notice_result.json `
  --create-package
```

### 19.4 Re-run mapping quality gate with corrected package metric

```powershell
python scripts/check_topic5_mapping_quality_gate.py `
  --mode global_assignment `
  --verify-package
```

### 19.5 Re-run alignment gate

```powershell
python scripts/check_topic5_alignment_gate.py
```

### 19.6 Full verification

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Optional frontend:

```powershell
Push-Location frontend
npm.cmd test
Pop-Location
```

---

## 20. Required Reports

Generate or update:

```text
reports/schema_pack_assertions_all.json
reports/schema_pack_assertions_all.md
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
reports/topic5_inline_announcement_result.json
reports/topic5_inline_event_notice_result.json
reports/topic5_alignment_gate_report.json
reports/topic5_alignment_gate_report.md
docs/openapi.json
```

Do not name the report:

```text
quality_report.json
```

Preferred report name:

```text
conversion_output_assertion_report.json
```

For aggregate SchemaPack evaluation:

```text
schema_pack_assertions_all.json
schema_pack_assertions_all.md
```

---

## 21. Phase 3 Acceptance Gate

Phase 3 is complete only if:

```text
[ ] Carry-over fixes from Phase 2 are complete.
[ ] schema_pack.yaml exists for announcement_doc and event_notice_doc.
[ ] conversion_output_assertions.yaml exists for announcement_doc and event_notice_doc.
[ ] SchemaPack validator validates manifest and output assertions.
[ ] ConversionOutputAssertionService exists.
[ ] Topic5 inline conversion supports optional output_assertions.
[ ] Response includes conversion_output_assertion_report when assertions are supplied.
[ ] Assertion errors affect status as specified.
[ ] Warnings do not affect completed status.
[ ] Existing conversions still work without assertions.
[ ] SchemaPack assertion evaluator exists.
[ ] SchemaPack assertion eval passes for all examples.
[ ] Badcase regression is checked.
[ ] Package 1.1 compatibility is preserved.
[ ] Documentation states this is not Topic 6.
[ ] Alignment gate rejects Topic 6 overreach wording.
[ ] Full verification passes.
```

---

## 22. Recommended Success Statement

After Phase 3 passes, use this statement:

```text
Phase 3 upgrades SchemaPack from example configuration files into a reusable Topic 5 conversion contract. Each SchemaPack can declare target schema, metadata template, mapping rules, content organization parameters, optional router hints, conversion output assertions, examples, tests, and badcases. The conversion pipeline can generate a conversion_output_assertion_report for field-level, chunk-level, and artifact-level correctness checks. This report complements Schema validation and package verification, preserves Package 1.1 compatibility, and does not implement Topic 6 quality scoring, quality grading, routing recommendation, semantic fidelity evaluation, or LLM-as-Judge.
```

---

## 23. What Not to Do

Do not:

```text
- build a quality score
- build a quality grade
- build route suggestions
- build publish/reject decisions
- build LLM-as-Judge
- build semantic fidelity evaluation
- build over-cleaning detection
- make assertion report a required Package 1.1 artifact
- break conversion without assertions
- hardcode assertions inside backend services
- tune assertions using blind gold data
- claim production-grade quality inspection
```

---

## 24. Next Phase Preview

After Phase 3, the most task-aligned next phase should be:

```text
Phase 4: Dual-form Consistency and Downstream Consumability Gate
```

Recommended Phase 4 focus:

```text
JSON/Markdown/chunks consistency
source backlink coverage
manifest/checksum completeness
RAG JSONL export
training JSONL export
consumer contract evaluation
```

This is more aligned with Topic 5 than further expanding output assertions into quality inspection.
