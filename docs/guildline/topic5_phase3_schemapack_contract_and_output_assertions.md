# Phase 3 Execution Plan: SchemaPack Contract and Conversion Output Assertions

Version: 2.0  
Language: English  
Recommended branch: `feat/topic5-schemapack-contract`  
Recommended base branch: the accepted Phase 2 branch after all Phase 2 fixes are merged  
Primary objective: formalize SchemaPack as a versioned Topic 5 configuration contract and add deterministic conversion-output assertions without expanding the project into Topic 6 quality inspection.

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



## 0. Mandatory Scope Boundary

This section is normative. All implementation decisions in Phase 3 must comply with it.

### 0.1 Topic 5 responsibility

Topic 5 is responsible for:

```text
Normalized structured intermediate representation
+ Target Schema
+ Metadata template
+ Mapping rules
+ Content organization parameters
-> Field mapping and field operations
-> Schema-compliant structured output
-> Human-readable and machine-readable deliverables
-> Standardized result package
```

Phase 3 strengthens the configuration contract used by this conversion process.

### 0.2 What Phase 3 adds

Phase 3 adds:

```text
- a versioned SchemaPack manifest;
- explicit asset references;
- deterministic output assertions;
- validation of SchemaPack completeness and internal consistency;
- an assertion report for converted structured output;
- example-based and badcase-based SchemaPack regression checks;
- clear compatibility and versioning rules.
```

### 0.3 What Phase 3 does not add

Phase 3 must not implement Topic 6 responsibilities.

The following features are out of scope:

```text
- overall quality scores;
- quality grades such as A/B/C;
- weighted quality dimensions;
- publish / reject / rerun route recommendations;
- production release decisions;
- process-gate orchestration;
- PII compliance inspection;
- semantic fidelity evaluation;
- over-cleaning detection;
- readability scoring;
- LLM-as-Judge evaluation;
- model-calibrated quality assessment;
- anchor-level defect scoring for all governance stages.
```

### 0.4 Canonical terminology

Use the following canonical terms:

```text
SchemaPack contract
conversion output assertion
assertion definition
assertion issue
conversion assertion report
contract validation
```

Do not use the following terms for Phase 3 components:

```text
quality inspection agent
final inspection
quality score
quality grade
routing recommendation
publication gate
```

### 0.5 Canonical file and report names

Use:

```text
output_assertions.yaml
conversion_assertion_report.json
ConversionAssertionService
ConversionAssertionReport
```

Do not introduce the following as canonical names:

```text
quality_rules.yaml
quality_report.json
QualityRuleService
```

If an earlier experimental branch already introduced those names, migrate them to the canonical names in this document. A temporary compatibility alias may be accepted only when required to preserve existing examples, and it must emit a deprecation warning.

### 0.6 Topic 11 boundary

Phase 3 may preserve or improve the interface by which Topic 5 calls a content-organization provider.

Phase 3 must not implement the complete Topic 11 research scope, including:

```text
- retrieval-based optimization of chunking;
- Recall@k or nDCG closed-loop optimization;
- semantic chunking research;
- full RAG evaluation;
- training QA generation research.
```

Those concerns remain external or deferred.

---

# 1. Phase 2 Carry-over Fixes

Complete these fixes before adding the new SchemaPack contract features. They are required Phase 3 work.

---

## 1.1 Fix invalid regular-expression handling

### Problem

The current SchemaPack validator may call `re.compile()` directly in a Boolean expression. Invalid patterns can raise `re.error` and terminate validation instead of producing a normal contract error.

### Files

```text
scripts/validate_schema_pack.py
backend/tests/test_schema_pack_contract_validation.py
```

### Required implementation

Use explicit exception handling:

```python
try:
    re.compile(str(pattern))
except re.error as exc:
    errors.append(f"{location} contains an invalid regular expression: {exc}")
```

Apply this rule to all user-configurable regular expressions, including:

```text
mapping rule regex patterns
negative-pair source patterns
output assertion regex patterns
router regex patterns, if applicable
```

### Required tests

```python
def test_invalid_mapping_regex_is_reported_without_crash():
    ...

def test_invalid_negative_pair_regex_is_reported_without_crash():
    ...

def test_invalid_output_assertion_regex_is_reported_without_crash():
    ...
```

### Acceptance criteria

```text
[ ] Invalid regex never crashes the contract validator.
[ ] The returned error identifies the exact file and logical path.
[ ] The validator exits non-zero only through its normal failed-validation path.
```

---

## 1.2 Correct package-related evaluation metrics

### Problem

A conversion response status must not be reported as package verification success when no package was generated and verified.

### Files

```text
scripts/eval_topic5_standard_uir_mapping.py
scripts/check_topic5_mapping_quality_gate.py
backend/tests/test_topic5_standard_uir_eval.py
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
```

### Required metric names

Use:

```text
conversion_success_rate
package_verifier_pass_rate
package_verified_count
```

Definitions:

```text
conversion_success:
  conversion completed or returned review_required without an execution error

package_verifier_pass:
  an actual package was created and the existing package verifier returned passed=true
```

### Required CLI option

```text
--verify-package
```

Behavior:

```text
default:
  false for fast local benchmark iteration

final committed gate:
  true
```

### Acceptance criteria

```text
[ ] No metric implies package verification when package creation is disabled.
[ ] Final committed reports use actual package verification.
[ ] Historical `package_pass_rate` is removed or explicitly marked deprecated.
```

---

## 1.3 Add per-schema mapping visibility

### Problem

Aggregate mapping metrics can hide weak schema families.

### Files

```text
scripts/eval_topic5_standard_uir_mapping.py
scripts/check_topic5_mapping_quality_gate.py
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
docs/交接/topic5_mapping_quality_phase2.md
```

### Required per-schema checks

Report:

```text
auto_precision
auto_recall
auto_f1
required_missing
badcase_violations
review_required_rate
sample_count
gold_mapping_count
```

Recommended policy for this phase:

```text
hard failure:
  per-schema required_missing > 0
  per-schema badcase_violations > 0

warning:
  per-schema auto_precision < 0.85
  per-schema auto_recall < 0.85
```

Do not silently hide warning-only failures.

### Acceptance criteria

```text
[ ] Aggregate and per-schema metrics appear in JSON and Markdown.
[ ] Weak schema families are listed in warnings.
[ ] Hard-failure and warning policies are documented.
```

---

## 1.4 Tighten MappingRepairService thresholds

### Problem

A candidate meeting only the review threshold must not be converted into an automatically accepted repair.

### Files

```text
backend/app/services/mapping_repair_service.py
backend/tests/test_mapping_repair_service.py
```

### Required thresholds

```text
repair_auto_accept_threshold = 0.82
repair_review_threshold = 0.62
```

### Required behavior

```text
score >= repair_auto_accept_threshold:
  accepted deterministic repair

repair_review_threshold <= score < repair_auto_accept_threshold:
  review-required repair candidate

score < repair_review_threshold:
  remain unmapped
```

### Required report fields

```json
{
  "accepted_repair_fields": [],
  "review_repair_fields": [],
  "unrepaired_fields": []
}
```

### Acceptance criteria

```text
[ ] No repair below the auto-accept threshold is marked accepted.
[ ] Review-level repairs remain visibly separate.
[ ] Regression tests cover all three threshold ranges.
```

---

## 1.5 Preserve the benchmark claim boundary

### Files

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/topic5_mapping_quality_phase2.md
reports/topic5_mapping_quality_gate_report.md
```

### Required wording

```text
The project demonstrates benchmark-level automatic field mapping performance within the declared Topic 5 standard UIR benchmark scope. It does not claim arbitrary-schema production performance or production shadow/blind performance.
```

### Acceptance criteria

```text
[ ] No document overclaims production-grade arbitrary-schema mapping.
[ ] Benchmark scope, dataset scope, and split policy are stated.
```

---

# 2. Phase 3 Goal

Formalize SchemaPack as the complete, versioned, reusable configuration unit for Topic 5 conversion.

After Phase 3, a SchemaPack must be able to declare:

```text
- its identity and version;
- the target schema;
- the metadata template;
- mapping rules;
- content organization parameters;
- optional routing hints;
- deterministic conversion output assertions;
- examples;
- expected results;
- badcases;
- compatibility requirements.
```

The conversion pipeline must be able to:

```text
1. validate a SchemaPack before execution;
2. load all referenced assets through one manifest;
3. execute Topic 5 conversion using the pack;
4. evaluate deterministic assertions on converted output;
5. generate a machine-readable assertion report;
6. preserve source evidence and field paths in assertion issues;
7. remain fully functional when assertions are absent;
8. preserve the existing Package 1.1 contract.
```

---

# 3. Deliverables

Phase 3 must deliver:

```text
schema_pack.yaml
output_assertions.yaml
schema_pack_contract.schema.json or equivalent typed contract
ConversionAssertionService
conversion_assertion_report.json
expanded SchemaPack validator
SchemaPack regression evaluator
example SchemaPacks
badcase fixtures
unit and integration tests
contract documentation
updated acceptance evidence
```

---

# 4. Target SchemaPack Layout

Use the following canonical layout:

```text
schema_packs/
  schema_pack_contract.schema.json
  output_assertions_contract.schema.json

  examples/
    announcement_doc/
      schema_pack.yaml
      target_schema.json
      metadata_template.json
      mapping_rules.yaml
      content_org.yaml
      output_assertions.yaml
      router_rules.yaml

      examples/
        example_001_uir.json
        example_001_request.json
        example_001_expected_content.json
        example_001_expected_assertions.json

      badcases/
        badcase_001_uir.json
        badcase_001_expected_assertions.json
        negative_pairs.jsonl

    event_notice_doc/
      schema_pack.yaml
      target_schema.json
      metadata_template.json
      mapping_rules.yaml
      content_org.yaml
      output_assertions.yaml
      router_rules.yaml
      examples/
      badcases/
```

At minimum, fully migrate:

```text
announcement_doc
event_notice_doc
```

For other example packs, add at least a valid manifest or document why migration is deferred.

---

# 5. Task 3.1: Add the SchemaPack Manifest

## 5.1 File

Create:

```text
schema_pack.yaml
```

inside each migrated SchemaPack.

## 5.2 Canonical manifest example

```yaml
contract_version: "1.0"
schema_pack_id: "announcement_doc"
schema_pack_version: "1.0.0"

display_name: "Announcement Document"
description: "Configuration pack for converting normalized UIR into announcement documents."
status: "example"
owner: "course-team"

compatibility:
  min_agent_version: "1.0.0"
  max_agent_version: null
  input_uir_version: "1.0"
  package_contract_version: "1.1"

assets:
  target_schema: "target_schema.json"
  metadata_template: "metadata_template.json"
  mapping_rules: "mapping_rules.yaml"
  content_org: "content_org.yaml"
  output_assertions: "output_assertions.yaml"
  router_rules: "router_rules.yaml"

execution:
  default_mapping_mode: "global_assignment"
  allow_llm_fallback: false
  include_assertion_report_in_package: false

supported_input:
  normalized_uir_required: true
  source_formats:
    - "standard_uir"
  languages:
    - "zh-CN"
    - "en-US"

claim_boundary:
  benchmark_scope: true
  production_ready: false
  notes: "Example configuration and benchmark asset; not a production capability boundary."
```

## 5.3 Required manifest fields

Required:

```text
contract_version
schema_pack_id
schema_pack_version
display_name
description
status
owner
compatibility
assets
execution
supported_input
claim_boundary
```

## 5.4 ID consistency rules

The following IDs must match:

```text
schema_pack.yaml.schema_pack_id
target_schema.json.schema_id
metadata_template template/schema reference
mapping_rules schema reference, when present
content_org schema reference, when present
output_assertions.yaml.schema_id
router_rules schema reference, when present
```

Do not silently normalize conflicting IDs.

## 5.5 Semantic versioning

Use semantic version format:

```text
MAJOR.MINOR.PATCH
```

Interpretation:

```text
MAJOR:
  incompatible contract or output behavior

MINOR:
  backward-compatible field, assertion, or configuration addition

PATCH:
  bug fix or documentation-only correction without expected output change
```

## 5.6 Acceptance criteria

```text
[ ] announcement_doc has a valid schema_pack.yaml.
[ ] event_notice_doc has a valid schema_pack.yaml.
[ ] All referenced assets exist.
[ ] Cross-file identifiers are consistent.
[ ] Semantic versions are validated.
```

---

# 6. Task 3.2: Define the SchemaPack Manifest Contract

## 6.1 Files

Create or update:

```text
schema_packs/schema_pack_contract.schema.json
backend/app/schemas/schema_pack_contract.py
```

Use either JSON Schema plus Pydantic, or one canonical typed model with generated JSON Schema. Do not maintain two conflicting definitions.

Recommended approach:

```text
Pydantic model is runtime source of truth.
Generated JSON Schema is committed for external documentation and tooling.
```

## 6.2 Required Pydantic models

```python
class SchemaPackCompatibility(StrictBaseModel):
    min_agent_version: str
    max_agent_version: str | None = None
    input_uir_version: str
    package_contract_version: str


class SchemaPackAssets(StrictBaseModel):
    target_schema: str
    metadata_template: str
    mapping_rules: str
    content_org: str
    output_assertions: str | None = None
    router_rules: str | None = None


class SchemaPackExecution(StrictBaseModel):
    default_mapping_mode: Literal["legacy", "global_assignment"] = "global_assignment"
    allow_llm_fallback: bool = False
    include_assertion_report_in_package: bool = False


class SchemaPackSupportedInput(StrictBaseModel):
    normalized_uir_required: bool = True
    source_formats: list[str]
    languages: list[str] = Field(default_factory=list)


class SchemaPackClaimBoundary(StrictBaseModel):
    benchmark_scope: bool = True
    production_ready: bool = False
    notes: str


class SchemaPackManifest(StrictBaseModel):
    contract_version: str
    schema_pack_id: str
    schema_pack_version: str
    display_name: str
    description: str
    status: Literal["example", "experimental", "stable", "deprecated"]
    owner: str

    compatibility: SchemaPackCompatibility
    assets: SchemaPackAssets
    execution: SchemaPackExecution
    supported_input: SchemaPackSupportedInput
    claim_boundary: SchemaPackClaimBoundary
```

## 6.3 Path safety rules

All asset paths must:

```text
- be relative paths;
- remain inside the SchemaPack directory;
- reject `..` traversal;
- reject absolute paths;
- resolve to regular files;
- use UTF-8 text for text assets.
```

## 6.4 Acceptance criteria

```text
[ ] Runtime manifest loading uses strict typed validation.
[ ] Unknown fields are rejected unless the project has an explicit extension mechanism.
[ ] Unsafe asset paths are rejected.
[ ] JSON Schema is generated or synchronized.
```

---

# 7. Task 3.3: Define `output_assertions.yaml`

## 7.1 Purpose

`output_assertions.yaml` declares deterministic conditions that a Topic 5 converted structured output must satisfy.

It does not calculate an overall quality score.

It does not issue a publish/reject route.

It does not perform semantic judgment.

## 7.2 Canonical file example

```yaml
contract_version: "1.0"
schema_id: "announcement_doc"
assertion_set_version: "1.0.0"

defaults:
  severity: "error"
  missing_optional_field: "skip"

assertions:
  - assertion_id: "title_non_empty"
    path: "$.data.title"
    operator: "non_empty"
    severity: "error"
    message: "The converted title must not be empty."

  - assertion_id: "publish_date_iso"
    path: "$.data.publish_date"
    operator: "date_format"
    severity: "error"
    optional: true
    parameters:
      formats:
        - "%Y-%m-%d"
    message: "Publish date must use YYYY-MM-DD."

  - assertion_id: "body_minimum_length"
    path: "$.data.body"
    operator: "text_length"
    severity: "warning"
    parameters:
      min: 10
    message: "The converted body is unusually short."

  - assertion_id: "source_url_format"
    path: "$.metadata.source_url"
    operator: "url_like"
    severity: "warning"
    optional: true
    message: "Source URL should use HTTP or HTTPS."

  - assertion_id: "dates_must_differ"
    path: "$.data.publish_date"
    operator: "not_equal_to_path"
    severity: "warning"
    optional: true
    parameters:
      other_path: "$.metadata.retrieved_at"
    message: "Publish date should not be copied from retrieval time."
```

## 7.3 Supported severities

```text
error
warning
```

Do not introduce:

```text
score
grade
route
publish
reject
```

Optional future severity:

```text
review
```

Do not add it in Phase 3 unless the current runtime already has a clear, tested need. Prefer only `error` and `warning` for this phase.

## 7.4 Supported operators

Implement only deterministic operators.

Required Phase 3 operators:

```text
exists
non_empty
type_is
date_format
datetime_format
regex_match
enum_allowed
number_range
text_length
array_length
url_like
equal_to_path
not_equal_to_path
```

Optional operators only if required by a real example:

```text
starts_with
ends_with
contains
unique_items
```

Do not implement semantic operators such as:

```text
summary_is_faithful
text_is_readable
entity_is_correct
content_is_high_quality
```

## 7.5 Operator definitions

### `exists`

Passes when the JSON path resolves.

Parameters:

```yaml
parameters: {}
```

### `non_empty`

Fails for:

```text
null
empty string
whitespace-only string
empty list
empty object
```

### `type_is`

Supported expected types:

```text
string
number
integer
boolean
array
object
null
```

Example:

```yaml
parameters:
  expected: "string"
```

### `date_format`

Value must parse using at least one configured format.

```yaml
parameters:
  formats:
    - "%Y-%m-%d"
```

### `datetime_format`

```yaml
parameters:
  formats:
    - "%Y-%m-%d %H:%M"
    - "%Y-%m-%dT%H:%M:%S"
```

### `regex_match`

Use full or search mode explicitly:

```yaml
parameters:
  pattern: "^[A-Z]{2}-\\d{6}$"
  mode: "fullmatch"
```

Supported modes:

```text
search
match
fullmatch
```

### `enum_allowed`

```yaml
parameters:
  values:
    - "draft"
    - "published"
    - "archived"
```

### `number_range`

```yaml
parameters:
  min: 0
  max: 100
  inclusive_min: true
  inclusive_max: true
```

### `text_length`

```yaml
parameters:
  min: 10
  max: 5000
```

### `array_length`

```yaml
parameters:
  min: 1
  max: 50
```

### `url_like`

Accepted schemes:

```text
http
https
```

Do not perform remote URL requests.

### `equal_to_path`

```yaml
parameters:
  other_path: "$.metadata.document_id"
```

### `not_equal_to_path`

```yaml
parameters:
  other_path: "$.metadata.retrieved_at"
```

## 7.6 Missing-value behavior

Each assertion supports:

```yaml
optional: true
```

Rules:

```text
optional=false and path missing:
  issue with configured severity

optional=true and path missing:
  skipped, no issue

path exists but value is null:
  operator evaluates normally
```

## 7.7 Unique identifiers

`assertion_id` must be unique within a SchemaPack.

Use stable IDs because reports and regression fixtures reference them.

## 7.8 Acceptance criteria

```text
[ ] Contract is deterministic and versioned.
[ ] No semantic or LLM-based operator is implemented.
[ ] Assertion IDs are unique.
[ ] All JSON paths are syntactically validated.
[ ] Regex patterns are compiled during contract validation.
```

---

# 8. Task 3.4: Add Assertion Contract Models

## 8.1 Files

```text
backend/app/schemas/conversion_assertions.py
schema_packs/output_assertions_contract.schema.json
```

## 8.2 Required models

```python
class AssertionDefaults(StrictBaseModel):
    severity: Literal["error", "warning"] = "error"
    missing_optional_field: Literal["skip"] = "skip"


class ConversionAssertionDefinition(StrictBaseModel):
    assertion_id: str
    path: str
    operator: Literal[
        "exists",
        "non_empty",
        "type_is",
        "date_format",
        "datetime_format",
        "regex_match",
        "enum_allowed",
        "number_range",
        "text_length",
        "array_length",
        "url_like",
        "equal_to_path",
        "not_equal_to_path",
    ]
    severity: Literal["error", "warning"] | None = None
    optional: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


class ConversionAssertionConfig(StrictBaseModel):
    contract_version: str
    schema_id: str
    assertion_set_version: str
    defaults: AssertionDefaults = Field(default_factory=AssertionDefaults)
    assertions: list[ConversionAssertionDefinition]
```

## 8.3 Operator-specific parameter validation

Do not postpone all validation to runtime.

Validate required parameters during contract loading:

```text
type_is:
  expected required

date_format:
  formats required and non-empty

datetime_format:
  formats required and non-empty

regex_match:
  pattern required
  mode must be search/match/fullmatch

enum_allowed:
  values required

number_range:
  at least min or max required

text_length:
  at least min or max required

array_length:
  at least min or max required

equal_to_path / not_equal_to_path:
  other_path required
```

Reject unsupported parameters when practical.

## 8.4 Acceptance criteria

```text
[ ] Invalid operator parameters fail SchemaPack contract validation.
[ ] Unknown operators fail validation.
[ ] Unknown severities fail validation.
[ ] Generated JSON Schema is committed.
```

---

# 9. Task 3.5: Implement JSON Path Resolution

## 9.1 Files

```text
backend/app/services/json_path_service.py
backend/tests/test_json_path_service.py
```

## 9.2 Supported path subset

Do not add a full JSONPath dependency unless already present.

Support a small, documented subset:

```text
$.data.title
$.metadata.source_url
$.chunks
$.chunks[0].text
```

Required syntax:

```text
root marker: $
object key: .name
array index: [0]
```

Not required:

```text
wildcards
filters
recursive descent
script expressions
```

## 9.3 Return type

```python
class PathResolution(StrictBaseModel):
    found: bool
    value: Any = None
    normalized_path: str
    error: str | None = None
```

## 9.4 Safety

Path resolution must:

```text
- never execute code;
- never interpret Python expressions;
- never mutate input;
- return a structured resolution error.
```

## 9.5 Acceptance criteria

```text
[ ] Object paths work.
[ ] Array index paths work.
[ ] Missing paths return found=false.
[ ] Invalid syntax returns a structured error.
[ ] Input objects are not modified.
```

---

# 10. Task 3.6: Implement ConversionAssertionService

## 10.1 Files

```text
backend/app/services/conversion_assertion_service.py
backend/app/schemas/conversion_assertion_report.py
backend/tests/test_conversion_assertion_service.py
```

## 10.2 Service interface

```python
class ConversionAssertionService:
    def evaluate(
        self,
        *,
        task_id: str,
        schema_pack_id: str,
        schema_pack_version: str,
        schema_id: str,
        content_json: dict[str, Any],
        assertion_config: ConversionAssertionConfig,
        mapping_report: dict[str, Any] | None = None,
    ) -> ConversionAssertionReport:
        ...
```

## 10.3 Report models

```python
class ConversionAssertionIssue(StrictBaseModel):
    assertion_id: str
    severity: Literal["error", "warning"]
    path: str
    operator: str
    message: str

    expected: Any | None = None
    actual_preview: Any | None = None

    source_path: str | None = None
    source_candidate_id: str | None = None
    mapping_method: str | None = None


class ConversionAssertionResult(StrictBaseModel):
    assertion_id: str
    status: Literal["passed", "failed", "skipped"]
    severity: Literal["error", "warning"]
    path: str
    operator: str


class ConversionAssertionReport(StrictBaseModel):
    contract_version: str = "1.0"
    task_id: str
    schema_pack_id: str
    schema_pack_version: str
    schema_id: str
    assertion_set_version: str

    passed: bool
    total_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    error_count: int
    warning_count: int

    results: list[ConversionAssertionResult]
    issues: list[ConversionAssertionIssue]

    generated_at: str
```

## 10.4 Pass semantics

```text
passed = error_count == 0
```

Warnings do not make `passed=false`.

No score is calculated.

No grade is calculated.

No route recommendation is generated.

## 10.5 Evidence enrichment

When `mapping_report` is available, enrich an assertion issue with the mapping evidence for the target field.

Recommended lookup:

```text
assertion path $.data.publish_date
-> target field publish_date
-> mapping_report.mappings[target_field_id=publish_date]
-> source_path, candidate_id, mapping_method
```

If evidence cannot be found, leave evidence fields null. Do not fabricate evidence.

## 10.6 Actual-value redaction

Do not copy unbounded output values into reports.

Rules:

```text
strings:
  maximum 200 characters

arrays:
  first 5 items or a count summary

objects:
  first 10 keys or a key summary
```

## 10.7 Determinism

For identical:

```text
content_json
assertion config
mapping report
software version
```

the report content must be deterministic except for `generated_at`.

Sort issues by:

```text
severity
assertion_id
path
```

## 10.8 Acceptance criteria

```text
[ ] Every required operator is implemented.
[ ] Error and warning semantics are correct.
[ ] Missing optional fields are skipped.
[ ] Mapping evidence is included when available.
[ ] Reports contain no score, grade, or route.
[ ] Report ordering is deterministic.
```

---

# 11. Task 3.7: Load SchemaPack Assets Through the Manifest

## 11.1 Files

```text
backend/app/services/schema_pack_service.py
backend/app/schemas/schema_pack_contract.py
backend/tests/test_schema_pack_service.py
```

## 11.2 Required service methods

```python
def load_manifest(self, schema_pack_id: str) -> SchemaPackManifest:
    ...

def load_target_schema(self, schema_pack_id: str) -> dict[str, Any]:
    ...

def load_metadata_template(self, schema_pack_id: str) -> dict[str, Any]:
    ...

def load_mapping_rules(self, schema_pack_id: str) -> dict[str, Any]:
    ...

def load_content_org(self, schema_pack_id: str) -> dict[str, Any]:
    ...

def load_output_assertions(
    self,
    schema_pack_id: str,
) -> ConversionAssertionConfig | None:
    ...

def load_router_rules(self, schema_pack_id: str) -> dict[str, Any] | None:
    ...
```

All asset paths must come from the manifest.

Do not guess filenames after the manifest is introduced.

## 11.3 YAML loading

Use a safe YAML loader.

Required:

```python
yaml.safe_load(...)
```

Do not:

```text
- use unsafe YAML object construction;
- write a partial line-based parser for nested assertion configuration;
- silently drop unsupported YAML structures.
```

If PyYAML is not already a dependency:

```text
- add it explicitly to the backend dependency file;
- document the dependency;
- update lock files if the repository uses them.
```

## 11.4 Optional assertions

If `assets.output_assertions` is null or absent:

```text
conversion proceeds normally
conversion_assertion_report = null
```

Do not fail legacy SchemaPacks solely because assertions are absent unless the manifest contract version explicitly requires them.

## 11.5 Acceptance criteria

```text
[ ] Assets are loaded only through manifest references.
[ ] YAML uses safe loading.
[ ] Legacy packs without assertions remain executable under a documented compatibility mode.
[ ] Missing required assets fail with precise messages.
```

---

# 12. Task 3.8: Expand the SchemaPack Validator

## 12.1 Files

```text
scripts/validate_schema_pack.py
backend/app/services/schema_pack_contract_validator.py
backend/tests/test_schema_pack_contract_validation.py
```

Recommended architecture:

```text
validator logic in backend service
CLI script as a thin wrapper
```

Do not keep complex validation logic only inside the CLI.

## 12.2 Validation layers

The validator must run these layers in order:

```text
1. directory and manifest discovery
2. manifest structural validation
3. asset path safety validation
4. required asset existence
5. per-asset structural validation
6. cross-file identifier consistency
7. target-field reference validation
8. regex and path syntax validation
9. example fixture validation
10. badcase fixture validation
```

## 12.3 Cross-file field validation

Assertion paths under `$.data.<field>` must reference fields declared by the target schema.

Assertion paths under `$.metadata.<field>` must reference fields declared by the metadata template or approved standard metadata fields.

Do not allow silent typos such as:

```text
$.data.publishDate
```

when the schema field is:

```text
publish_date
```

## 12.4 Contract report

CLI output must support:

```text
human-readable console output
JSON report
non-zero exit code on failure
```

Recommended CLI:

```powershell
python scripts/validate_schema_pack.py `
  schema_packs/examples/announcement_doc `
  --out reports/schema_pack_contract_announcement_doc.json
```

JSON example:

```json
{
  "status": "passed",
  "schema_pack_id": "announcement_doc",
  "schema_pack_version": "1.0.0",
  "errors": [],
  "warnings": [],
  "validated_assets": [
    "schema_pack.yaml",
    "target_schema.json",
    "metadata_template.json",
    "mapping_rules.yaml",
    "content_org.yaml",
    "output_assertions.yaml",
    "router_rules.yaml"
  ]
}
```

## 12.5 Required validator tests

```text
valid pack passes
missing manifest fails
unsafe path fails
missing required asset fails
schema ID mismatch fails
duplicate assertion ID fails
unknown assertion operator fails
invalid assertion path fails
unknown target field fails
invalid regex fails without crash
invalid date format configuration fails
unsupported severity fails
```

## 12.6 Acceptance criteria

```text
[ ] Contract validation is available as reusable service logic.
[ ] CLI produces JSON evidence.
[ ] All validation errors include asset and logical location.
[ ] Invalid packs never partially execute in strict mode.
```

---

# 13. Task 3.9: Integrate Assertions into Topic 5 Conversion

## 13.1 Files

```text
backend/app/schemas/topic5_convert.py
backend/app/services/topic5_conversion_service.py
backend/app/services/task_execution_service.py
backend/tests/test_topic5_conversion_assertion_integration.py
```

## 13.2 Inline request compatibility

Support optional inline assertions:

```python
output_assertions: ConversionAssertionConfig | None = None
```

Do not require inline assertions.

A normal Topic 5 request remains:

```text
UIR
+ target schema
+ metadata template
+ mapping rules
+ content organization parameters
```

Assertions are an optional extension of the conversion contract.

## 13.3 Registered SchemaPack execution

When a SchemaPack is selected:

```text
1. load manifest;
2. validate compatibility;
3. load required assets;
4. execute mapping and transformation;
5. run existing Schema validation;
6. evaluate output assertions when configured;
7. write conversion_assertion_report.json;
8. continue package creation.
```

## 13.4 Response model

Add:

```python
conversion_assertion_report: dict[str, Any] | None = None
```

Do not add:

```python
quality_score
quality_grade
route_recommendation
```

## 13.5 Conversion status behavior

Use the following limited semantics:

```text
assertion report has no errors:
  assertion stage passed

assertion report has warnings only:
  conversion may remain completed

assertion report has one or more errors:
  conversion status becomes review_required by default

strict_output_assertions=true and assertion errors exist:
  conversion status becomes failed
```

This status concerns whether the Topic 5 conversion output satisfies its declared SchemaPack contract. It is not a Topic 6 publication or governance route recommendation.

## 13.6 Options

Support:

```json
{
  "strict_output_assertions": false,
  "include_assertion_report_in_package": false
}
```

Manifest defaults may be overridden only if the existing request-option precedence policy allows it.

Document precedence explicitly:

```text
request option
> manifest execution default
> application default
```

## 13.7 Acceptance criteria

```text
[ ] Conversion works without assertions.
[ ] Passing assertions produce a passed report.
[ ] Warning-only assertions do not fail conversion.
[ ] Error assertions produce review_required by default.
[ ] Strict mode can fail the conversion.
[ ] No quality score or route recommendation is introduced.
```

---

# 14. Task 3.10: Write and Persist the Assertion Report

## 14.1 Task workspace artifact

Write:

```text
tasks/<task_id>/conversion_assertion_report.json
```

Add the artifact path to the task execution snapshot:

```json
{
  "artifacts": {
    "conversion_assertion_report": "tasks/<task_id>/conversion_assertion_report.json"
  }
}
```

## 14.2 Atomic writing

Write using the existing atomic file-writing helper.

Do not leave partially written reports.

## 14.3 Report immutability

The report is execution evidence.

After package creation, do not rewrite it in place except through an explicit task rerun that creates a new task or versioned execution record.

## 14.4 Acceptance criteria

```text
[ ] Report is persisted for registered tasks.
[ ] Report path is exposed in task artifacts.
[ ] Writes are atomic.
[ ] Repeated identical runs produce equivalent report content.
```

---

# 15. Task 3.11: Preserve Package 1.1 Compatibility

## 15.1 Default policy

`conversion_assertion_report.json` is a task-side report by default.

It is not a required Package 1.1 artifact.

## 15.2 Optional package inclusion

When:

```text
include_assertion_report_in_package = true
```

the package may include:

```text
reports/conversion_assertion_report.json
```

Manifest entry:

```json
{
  "path": "reports/conversion_assertion_report.json",
  "role": "conversion_assertion_report",
  "required": false,
  "media_type": "application/json"
}
```

## 15.3 Package verifier

The existing Package 1.1 verifier must:

```text
- continue to pass packages without the assertion report;
- verify checksum if the optional report is included;
- reject a manifest entry whose checksum is incorrect;
- not make the optional report required.
```

## 15.4 Acceptance criteria

```text
[ ] Existing Package 1.1 fixtures remain valid.
[ ] Optional assertion report can be packaged.
[ ] Package checksum verification covers it when present.
[ ] No existing required artifact is removed or renamed.
```

---

# 16. Task 3.12: Migrate Example SchemaPacks

## 16.1 Required packs

Fully migrate:

```text
announcement_doc
event_notice_doc
```

Each must include:

```text
schema_pack.yaml
target_schema.json
metadata_template.json
mapping_rules.yaml
content_org.yaml
output_assertions.yaml
router_rules.yaml
examples/
badcases/
```

## 16.2 Announcement assertions

Recommended assertions:

```text
title exists and non-empty
body exists and non-empty
publish_date uses configured format when present
source URL is URL-like when present
publish_date is not equal to retrieved_at when both are present
```

## 16.3 Event notice assertions

Recommended assertions:

```text
title exists and non-empty
organizer exists and non-empty
event_time uses a configured datetime format
body exists and non-empty
event_time is not equal to publish_date when both are present
event_time is not equal to retrieved_at when both are present
```

## 16.4 Avoid redundant assertions

Do not duplicate every target-schema rule in assertions.

Use:

```text
target schema:
  type, required, allowed values where natively supported

output assertions:
  cross-field rules, normalized formatting, additional deterministic output expectations
```

## 16.5 Acceptance criteria

```text
[ ] Both packs pass contract validation.
[ ] Both packs pass their positive examples.
[ ] Both packs fail their intended badcases.
[ ] Assertions add value beyond basic Schema validation.
```

---

# 17. Task 3.13: Add Positive Examples and Badcases

## 17.1 Positive fixtures

For each migrated pack:

```text
examples/example_001_uir.json
examples/example_001_request.json
examples/example_001_expected_content.json
examples/example_001_expected_assertions.json
```

Expected assertion fixture example:

```json
{
  "passed": true,
  "error_count": 0,
  "warning_count": 0,
  "expected_results": {
    "title_non_empty": "passed",
    "publish_date_iso": "passed"
  }
}
```

## 17.2 Badcase fixtures

At minimum:

### Announcement badcase

```text
retrieved_at incorrectly used as publish_date
```

Expected:

```text
dates_must_differ -> failed
severity -> warning or error according to pack policy
```

### Event notice badcase

```text
publish_date incorrectly used as event_time
```

Expected:

```text
event_time_not_publish_date -> failed
```

## 17.3 Negative-pair consistency

When a badcase is already represented in mapping `negative_pairs`, preserve both checks:

```text
mapping layer:
  prevents or reviews the incorrect source-target assignment

output assertion layer:
  detects an invalid final deterministic relationship
```

Document that these are different safeguards, not accidental duplication.

## 17.4 Acceptance criteria

```text
[ ] Positive fixtures pass.
[ ] Badcases produce the exact expected assertion IDs.
[ ] Expected fixtures do not depend on timestamps or unstable ordering.
```

---

# 18. Task 3.14: Add SchemaPack Contract Evaluation

## 18.1 File

Create:

```text
scripts/eval_schema_pack_contracts.py
```

## 18.2 Purpose

Evaluate whether example SchemaPacks are:

```text
- structurally valid;
- internally consistent;
- executable;
- assertion-compatible;
- regression-protected.
```

This is not a Topic 6 quality evaluation.

## 18.3 CLI

Single pack:

```powershell
python scripts/eval_schema_pack_contracts.py `
  --schema-pack schema_packs/examples/announcement_doc `
  --out reports/schema_pack_contract_announcement_doc.json `
  --markdown reports/schema_pack_contract_announcement_doc.md
```

All examples:

```powershell
python scripts/eval_schema_pack_contracts.py `
  --all-examples `
  --out reports/schema_pack_contract_all.json `
  --markdown reports/schema_pack_contract_all.md
```

## 18.4 Required evaluation steps

For each pack:

```text
1. validate manifest;
2. validate assets;
3. run positive examples;
4. compare expected converted fields;
5. evaluate output assertions;
6. run badcases;
7. confirm expected assertion failures;
8. optionally create and verify Package 1.1;
9. write evidence report.
```

## 18.5 Report format

```json
{
  "status": "passed",
  "total_schema_packs": 2,
  "passed_schema_packs": 2,
  "failed_schema_packs": 0,
  "items": [
    {
      "schema_pack_id": "announcement_doc",
      "schema_pack_version": "1.0.0",
      "contract_valid": true,
      "positive_examples_passed": 1,
      "positive_examples_total": 1,
      "badcases_passed": 1,
      "badcases_total": 1,
      "assertion_errors": 0,
      "unexpected_assertion_failures": [],
      "package_verifier_passed": true
    }
  ]
}
```

Do not include:

```text
quality score
quality grade
route recommendation
```

## 18.6 Acceptance criteria

```text
[ ] Single-pack and all-pack modes work.
[ ] Reports are available as JSON and Markdown.
[ ] Unexpected positive-example assertion failures fail the evaluator.
[ ] Missing expected badcase failures fail the evaluator.
```

---

# 19. Task 3.15: Add a Phase 3 Gate

## 19.1 File

Create:

```text
scripts/check_schema_pack_contract_gate.py
```

## 19.2 Required checks

```text
all migrated manifests valid
all required assets present
all cross-file IDs consistent
all positive examples pass
all expected badcases detected
zero unexpected assertion errors
Package 1.1 compatibility preserved
Phase 2 mapping gate still passes
Topic 5 alignment gate still passes
```

## 19.3 CLI

```powershell
python scripts/check_schema_pack_contract_gate.py --fail-on-gate
```

## 19.4 Gate report

Write:

```text
reports/schema_pack_contract_gate_report.json
reports/schema_pack_contract_gate_report.md
```

Example:

```json
{
  "status": "passed",
  "checks": {
    "manifest_contracts": "passed",
    "asset_integrity": "passed",
    "cross_file_consistency": "passed",
    "positive_examples": "passed",
    "badcase_detection": "passed",
    "package_1_1_compatibility": "passed",
    "phase2_mapping_gate": "passed",
    "topic5_alignment_gate": "passed"
  },
  "failed_checks": [],
  "warnings": []
}
```

## 19.5 Acceptance criteria

```text
[ ] Gate exits non-zero only with --fail-on-gate.
[ ] Gate always writes a report.
[ ] Gate does not calculate a quality score.
[ ] Gate references the exact failing pack and fixture.
```

---

# 20. Task 3.16: Tests

## 20.1 Required test files

```text
backend/tests/test_json_path_service.py
backend/tests/test_conversion_assertion_service.py
backend/tests/test_schema_pack_service.py
backend/tests/test_schema_pack_contract_validation.py
backend/tests/test_topic5_conversion_assertion_integration.py
backend/tests/test_schema_pack_contract_eval.py
backend/tests/test_package_1_1_assertion_report_compatibility.py
```

## 20.2 Minimum test matrix

### Contract model

```text
valid manifest
invalid semantic version
unknown field
unsafe asset path
missing required asset reference
```

### Assertion configuration

```text
duplicate assertion ID
unknown operator
unknown severity
missing operator parameter
invalid JSON path
invalid regex
```

### JSON path

```text
object field
array index
missing key
invalid syntax
no mutation
```

### Assertion operators

```text
exists
non_empty
type_is
date_format
datetime_format
regex_match
enum_allowed
number_range
text_length
array_length
url_like
equal_to_path
not_equal_to_path
```

### Severity

```text
warning does not fail report
error fails report
optional missing field is skipped
required missing field fails
```

### Integration

```text
conversion without assertions remains compatible
conversion with passing assertions completes
warning-only conversion completes
error assertion returns review_required by default
strict assertion mode returns failed
mapping evidence appears in issue
```

### Package compatibility

```text
Package 1.1 without assertion report passes
Package 1.1 with optional assertion report passes
incorrect optional report checksum fails
```

### Evaluation

```text
positive examples pass
expected badcases pass
unexpected badcase behavior fails
all-example evaluation produces stable ordering
```

---

# 21. Task 3.17: Documentation

## 21.1 Files to create

```text
docs/schema_pack_contract.md
docs/conversion_output_assertions.md
docs/schema_pack_onboarding_checklist.md
```

## 21.2 Files to update

```text
README.md
docs/topic5_convert_api.md
docs/mapping_rules_contract.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
docs/交接/已知边界与后续事项.md
```

## 21.3 Required statement

Include exactly this conceptual boundary:

```text
Conversion output assertions are deterministic SchemaPack-scoped checks over Topic 5 converted output. They complement target-schema validation but do not implement Topic 6 quality scoring, grading, semantic fidelity evaluation, or routing recommendations.
```

## 21.4 Required SchemaPack definition

```text
A SchemaPack is the versioned external configuration contract for Topic 5. It declares the target schema, metadata template, mapping rules, content organization parameters, optional router hints, deterministic output assertions, examples, and badcases.
```

## 21.5 Required Topic 5 input statement

```text
The canonical Topic 5 input consists of normalized UIR, target schema, metadata template, mapping rules, and content organization parameters. A SchemaPack packages these configuration assets for reusable execution.
```

## 21.6 Required compatibility statement

```text
Output assertions are optional. Existing Package 1.1 deliverables and legacy Topic 5 requests remain supported.
```

## 21.7 Required non-goals section

Documentation must explicitly list:

```text
no quality score
no quality grade
no publication route
no semantic fidelity judgment
no LLM-as-Judge
no Topic 11 retrieval optimization
```

---

# 22. Implementation Order

Execute in this order:

```text
Step 1:
  Complete all Phase 2 carry-over fixes.

Step 2:
  Add manifest and assertion Pydantic models.

Step 3:
  Add JSON Schema generation/exports.

Step 4:
  Implement safe SchemaPack loading.

Step 5:
  Implement JSON path resolution.

Step 6:
  Implement ConversionAssertionService.

Step 7:
  Expand contract validator.

Step 8:
  Migrate announcement_doc and event_notice_doc.

Step 9:
  Add positive examples and badcases.

Step 10:
  Integrate assertions into inline and registered conversion.

Step 11:
  Add optional package artifact support.

Step 12:
  Add evaluator and Phase 3 gate.

Step 13:
  Update documentation and committed reports.

Step 14:
  Run all regression and full verification commands.
```

Do not start UI work in this phase.

---

# 23. Recommended Commit Structure

```text
fix: harden phase2 evidence and repair thresholds
feat: add versioned schema pack manifest
feat: add conversion output assertion contract
feat: add deterministic conversion assertion service
feat: integrate schema pack assertions into topic5 conversion
test: add schema pack examples and badcase regression
test: add schema pack contract gate
docs: document schema pack contract and scope boundary
```

Keep each commit independently testable.

---

# 24. Verification Commands

Run from repository root.

## 24.1 Contract validation

```powershell
python scripts/validate_schema_pack.py `
  schema_packs/examples/announcement_doc `
  --out reports/schema_pack_contract_announcement_doc.json

python scripts/validate_schema_pack.py `
  schema_packs/examples/event_notice_doc `
  --out reports/schema_pack_contract_event_notice_doc.json
```

## 24.2 SchemaPack contract evaluation

```powershell
python scripts/eval_schema_pack_contracts.py `
  --all-examples `
  --out reports/schema_pack_contract_all.json `
  --markdown reports/schema_pack_contract_all.md
```

## 24.3 Topic 5 inline examples

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

## 24.4 Phase 3 gate

```powershell
python scripts/check_schema_pack_contract_gate.py --fail-on-gate
```

## 24.5 Re-run Phase 2 mapping evidence

```powershell
python scripts/check_topic5_mapping_quality_gate.py `
  --mode global_assignment `
  --verify-package `
  --fail-on-gate
```

Adjust exact CLI syntax only to match the implemented parser; preserve the required semantics.

## 24.6 Topic 5 alignment

```powershell
python scripts/check_topic5_alignment_gate.py
```

## 24.7 Full backend verification

```powershell
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

## 24.8 Frontend regression, if frontend exists

```powershell
Push-Location frontend
npm.cmd test
Pop-Location
```

---

# 25. Required Generated Evidence

Commit or generate the following according to the repository evidence policy:

```text
reports/schema_pack_contract_announcement_doc.json
reports/schema_pack_contract_event_notice_doc.json
reports/schema_pack_contract_all.json
reports/schema_pack_contract_all.md
reports/schema_pack_contract_gate_report.json
reports/schema_pack_contract_gate_report.md
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
reports/topic5_alignment_gate_report.json
reports/topic5_alignment_gate_report.md
reports/topic5_inline_announcement_result.json
reports/topic5_inline_event_notice_result.json
docs/openapi.json
```

Do not commit temporary task workspaces or generated packages unless the repository already commits example packages.

---

# 26. Phase 3 Acceptance Checklist

Phase 3 is complete only when every item below is satisfied.

## 26.1 Carry-over fixes

```text
[ ] Invalid regex handling is fixed.
[ ] Package verification metrics are truthful.
[ ] Per-schema mapping metrics are visible.
[ ] Mapping repair thresholds are separated.
[ ] Benchmark claim boundaries are documented.
```

## 26.2 Contract

```text
[ ] schema_pack.yaml is canonical.
[ ] Manifest is strictly typed and versioned.
[ ] Asset paths are safe.
[ ] Cross-file IDs are consistent.
[ ] Semantic versioning is validated.
```

## 26.3 Assertions

```text
[ ] output_assertions.yaml is canonical.
[ ] Only deterministic operators are supported.
[ ] Assertions have stable unique IDs.
[ ] JSON paths and operator parameters are validated.
[ ] ConversionAssertionService is fully tested.
[ ] Reports contain no score, grade, or route.
```

## 26.4 Integration

```text
[ ] Assertions are optional.
[ ] Legacy conversion still works.
[ ] Registered SchemaPack execution loads assets through the manifest.
[ ] Assertion errors produce review_required by default.
[ ] Strict assertion mode is available.
[ ] Mapping evidence is preserved in assertion issues.
```

## 26.5 Package compatibility

```text
[ ] Package 1.1 remains valid without assertion reports.
[ ] Optional assertion reports can be packaged.
[ ] Checksums remain correct.
```

## 26.6 Examples and evaluation

```text
[ ] announcement_doc is fully migrated.
[ ] event_notice_doc is fully migrated.
[ ] Positive examples pass.
[ ] Expected badcases are detected.
[ ] SchemaPack contract evaluator passes.
[ ] Phase 3 gate passes.
[ ] Phase 2 mapping gate still passes.
[ ] Topic 5 alignment gate still passes.
[ ] Full test suite passes.
```

## 26.7 Boundary

```text
[ ] No Topic 6 scoring or routing system was added.
[ ] No semantic fidelity evaluator was added.
[ ] No LLM-as-Judge feature was added.
[ ] No complete Topic 11 research implementation was added.
[ ] Documentation explicitly states these boundaries.
```

---

# 27. Rejection Conditions

Reject the Phase 3 implementation if any of the following occurs:

```text
- `quality_score`, `quality_grade`, or route recommendation is added;
- assertion definitions invoke an LLM;
- semantic fidelity is claimed without an external Topic 6/12 service;
- Package 1.1 becomes incompatible;
- legacy Topic 5 requests require assertions;
- invalid regex crashes the validator;
- SchemaPack assets are loaded by guessed filenames instead of manifest references;
- badcase fixtures are tuned into implementation code;
- assertion reports omit the failing JSON path;
- reports claim production-grade arbitrary-schema capability;
- Phase 2 mapping metrics regress without documentation and approval.
```

---

# 28. Final Success Statement

Use the following statement after Phase 3 passes:

```text
Phase 3 formalizes SchemaPack as a versioned external configuration contract for Topic 5. A SchemaPack can declare the target schema, metadata template, mapping rules, content organization parameters, optional router hints, deterministic conversion output assertions, examples, and badcases. The Topic 5 conversion pipeline can validate the pack, execute conversion, and produce a traceable conversion assertion report without introducing Topic 6 quality scoring, grading, semantic evaluation, or routing responsibilities. Existing Package 1.1 and legacy conversion compatibility are preserved.
```

---

# 29. Next Phase Boundary

Do not implement the following in Phase 3.

The next phase should focus on:

```text
dual-form consistency
JSON / Markdown / chunks cross-link validation
artifact completeness
manifest and checksum completeness
one-click downstream export
RAG JSONL export
training JSONL export
consumer contract tests
```

This separation keeps Phase 3 centered on configuration contract correctness and keeps the project aligned with Topic 5.
