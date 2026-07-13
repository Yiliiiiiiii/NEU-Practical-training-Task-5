# Topic 5 Correction Execution Plan: Phase 0 and Phase 1

Version: 1.0  
Target branch: `fix/topic5-config-driven-correction`  
Target project: `Yiliiiiiiii/NEU-Practical-training-Task-5`  
Primary goal: make the project clearly conform to Topic 5 as a **configuration-driven data format standardization conversion agent**.

---

## 0. Executive Summary

The current correction branch already moves the project in the right direction:

```text
UIR
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
-> Config Validation
-> Generic Candidate Extraction
-> Schema-aware Mapping
-> Transform + Canonical
-> Render + Content Organization
-> Validate
-> Manifest + ZIP
-> Verify
```

However, several hardening issues must be fixed before the correction can be considered stable:

1. `Topic5ConversionService` currently determines final status mostly from `validation_report.passed`; it must also consider mapping review items, required unmapped fields, and package verifier status.
2. The API currently exposes `mapping_template`; Topic 5 wording expects `mapping_rules`. The API should accept `mapping_rules` while keeping `mapping_template` for backward compatibility.
3. Generic candidate extraction still partially depends on `uir.metadata.domain` in metadata candidate enrichment. Topic 5 inline mode must be domain-neutral.
4. `SchemaRouterService` still merges built-in five-family router signals by default. It should support a configurable no-built-in mode.
5. Documentation contains stale or inconsistent metric statements. These must be reconciled before merge.

This document defines two execution phases:

```text
Phase 0: Pre-merge hardening
Phase 1: Topic 5 mainline contract solidification
```

Phase 0 is mandatory before merging the correction branch.  
Phase 1 should be executed immediately after Phase 0 to make the project easier to explain, evaluate, and maintain.

---

# Phase 0: Pre-merge Hardening

## Phase 0 Goal

Make the current correction branch safe to merge into `main`.

After Phase 0, the project must be able to claim:

```text
The Topic 5 correction branch supports inline Topic 5 conversion input:
UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config.

The inline conversion API has correct status semantics.
Generic mode does not rely on domain-specific extraction logic.
Router built-in signals are configurable compatibility fallback, not system boundaries.
Documentation does not contain contradictory metric claims.
```

---

## Phase 0 Scope

### In scope

- Fix status computation in `Topic5ConversionService`.
- Add `mapping_rules` API alias while preserving `mapping_template`.
- Make generic candidate extraction truly domain-neutral.
- Add configurable built-in router signal behavior.
- Update related tests.
- Re-run and update correction gate reports.
- Clean documentation metric contradictions.

### Out of scope

- Do not redesign the whole mapper.
- Do not introduce global assignment yet.
- Do not build a front-end workbench yet.
- Do not introduce LLM auto-accept.
- Do not change Package 1.1 required artifact list unless absolutely necessary.
- Do not claim production blind/shadow recall 0.85.

---

## Phase 0 Branching Recommendation

Create a short-lived branch from the current correction branch:

```powershell
git checkout fix/topic5-config-driven-correction
git pull
git checkout -b fix/topic5-inline-hardening
```

After Phase 0 passes:

```powershell
git checkout fix/topic5-config-driven-correction
git merge --no-ff fix/topic5-inline-hardening
```

Recommended commit message:

```text
fix: harden topic5 inline correction gates
```

---

# Phase 0 Task 0.1: Harden Topic5ConversionService Status Semantics

## Problem

Current inline conversion status is too permissive. It can return `completed` when `validation_report.passed == true`, even if mapping still contains review-required items or required unmapped fields.

This is incorrect because Topic 5 output should distinguish:

```text
completed       -> no review required, no required field missing, validation passed, package passed if created
review_required -> mapping review exists, required field missing, or validation has issues
failed          -> package verifier failed or unrecoverable execution error
```

## Files to modify

```text
backend/app/services/topic5_conversion_service.py
backend/tests/test_topic5_convert_api.py
backend/tests/test_topic5_inline_schema_pack.py
```

Optionally add:

```text
backend/tests/test_topic5_inline_status.py
```

## Required implementation

In `Topic5ConversionService.convert()`, replace the final status logic.

### Current logic to replace

```python
status = "completed" if validation_report.passed else "review_required"
```

### Required new logic

Add a private helper method:

```python
class Topic5ConversionService:
    ...

    @staticmethod
    def _final_status(
        *,
        mapping_report: MappingReport,
        validation_passed: bool,
        verifier_passed: bool | None,
        create_package: bool,
    ) -> str:
        review_required_count = len(mapping_report.review_required_items)
        unmapped_required_count = sum(
            1 for item in mapping_report.unmapped if item.get("required")
        )

        if create_package and verifier_passed is False:
            return "failed"

        if review_required_count or unmapped_required_count or not validation_passed:
            return "review_required"

        return "completed"
```

Then use:

```python
verifier_passed = (
    bool(verifier_report.get("passed"))
    if isinstance(verifier_report, dict)
    else None
)

status = self._final_status(
    mapping_report=mapping_report,
    validation_passed=validation_report.passed,
    verifier_passed=verifier_passed,
    create_package=create_package,
)
```

If `verifier_report` is a Pydantic object before dumping, use:

```python
verifier_passed = package_result.verifier_report.passed
```

## Required tests

### Test 1: completed when no review and validation passes

Use existing announcement inline fixture.

Expected:

```python
assert response.status == "completed"
assert response.validation_report["passed"] is True
assert response.mapping_report["summary"]["review_required_count"] == 0
assert response.mapping_report["summary"]["required_unmapped_count"] == 0
```

### Test 2: review_required when mapping has review items

Create a request where one required field cannot be confidently mapped.

Example approach:

- Add a required field to target schema: `audience`.
- Do not provide source candidate or default.
- Run conversion.

Expected:

```python
assert response.status == "review_required"
assert response.mapping_report["summary"]["required_unmapped_count"] >= 1
```

### Test 3: review_required when validation fails

Create a request where output validation fails.

Expected:

```python
assert response.status == "review_required"
assert response.validation_report["passed"] is False
```

### Test 4: failed when package verifier fails

This may be hard to trigger without mocking. Use a unit test for `_final_status()`:

```python
def test_topic5_final_status_failed_when_package_verifier_fails():
    status = Topic5ConversionService._final_status(
        mapping_report=mapping_report_without_review,
        validation_passed=True,
        verifier_passed=False,
        create_package=True,
    )
    assert status == "failed"
```

## Acceptance criteria

```text
- Topic5 inline conversion no longer returns completed when review is required.
- Existing announcement demo still returns completed.
- Unit tests cover completed, review_required, and failed paths.
```

---

# Phase 0 Task 0.2: Add `mapping_rules` API Compatibility

## Problem

The current request model uses `mapping_template`, but Topic 5 expects "mapping rules" as an input. Functionally, `MappingTemplate` is the internal model for mapping rules, but the API vocabulary should support `mapping_rules`.

## Files to modify

```text
backend/app/schemas/topic5_convert.py
backend/app/services/topic5_conversion_service.py
examples/topic5_inline/announcement_convert_request.json
docs/openapi.json
backend/tests/test_topic5_convert_api.py
backend/tests/test_mapping_rules_config.py
```

## Required behavior

The API must support both of these payload styles:

### New preferred form

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

### Backward-compatible form

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

If both `mapping_rules` and `mapping_template` are provided:

- Accept the request only if they are identical, or
- Prefer `mapping_rules` and emit a response/report warning.

Recommended strict behavior:

```text
If both are provided and not equal, return 422.
If both are provided and equal, accept.
If only mapping_rules is provided, accept.
If only mapping_template is provided, accept but mark input alias as legacy.
If neither is provided, return 422.
```

## Required implementation

Modify `Topic5ConvertRequest`.

Recommended Pydantic v2 pattern:

```python
from pydantic import Field, model_validator


class Topic5ConvertRequest(StrictBaseModel):
    uir: UIRDocument
    target_schema: TargetSchema
    mapping_rules: MappingTemplate | None = None
    mapping_template: MappingTemplate | None = None
    metadata_template: MetadataTemplateConfig | None = None
    content_organization: ContentOrganizationConfig = Field(
        default_factory=ContentOrganizationConfig
    )
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_mapping_rules(self) -> "Topic5ConvertRequest":
        if self.mapping_rules is None and self.mapping_template is None:
            raise ValueError("mapping_rules is required")

        if self.mapping_rules is not None and self.mapping_template is not None:
            rules_payload = self.mapping_rules.model_dump(mode="json")
            template_payload = self.mapping_template.model_dump(mode="json")
            if rules_payload != template_payload:
                raise ValueError(
                    "mapping_rules and mapping_template cannot differ"
                )

        return self

    @property
    def effective_mapping_template(self) -> MappingTemplate:
        if self.mapping_rules is not None:
            return self.mapping_rules
        if self.mapping_template is not None:
            return self.mapping_template
        raise ValueError("mapping_rules is required")

    @property
    def mapping_input_name(self) -> str:
        if self.mapping_rules is not None:
            return "mapping_rules"
        return "mapping_template"
```

Then update `Topic5ConversionService`:

```python
template = TemplateService().validate_template(
    request.effective_mapping_template,
    schema,
)
```

Add to `mapping_report.summary`:

```python
mapping_report.summary["mapping_input_name"] = request.mapping_input_name
```

Add to `execution_snapshot`:

```python
"mapping_input_name": request.mapping_input_name,
```

## Example update

Update:

```text
examples/topic5_inline/announcement_convert_request.json
```

Change top-level field:

```json
"mapping_template": { ... }
```

to:

```json
"mapping_rules": { ... }
```

Optionally keep one test fixture using `mapping_template` to verify backward compatibility.

## Required tests

### Test 1: preferred mapping_rules accepted

```python
payload = topic5_payload()
payload["mapping_rules"] = payload.pop("mapping_template")
request = Topic5ConvertRequest.model_validate(payload)
assert request.mapping_input_name == "mapping_rules"
```

### Test 2: legacy mapping_template accepted

```python
payload = topic5_payload()
request = Topic5ConvertRequest.model_validate(payload)
assert request.mapping_input_name == "mapping_template"
```

### Test 3: missing mapping rules rejected

```python
payload = topic5_payload()
payload.pop("mapping_template", None)
payload.pop("mapping_rules", None)
with pytest.raises(ValidationError):
    Topic5ConvertRequest.model_validate(payload)
```

### Test 4: conflicting mapping_rules and mapping_template rejected

```python
payload = topic5_payload()
payload["mapping_rules"] = copy.deepcopy(payload["mapping_template"])
payload["mapping_template"]["schema_id"] = "other_schema"
with pytest.raises(ValidationError):
    Topic5ConvertRequest.model_validate(payload)
```

## Acceptance criteria

```text
- API accepts preferred mapping_rules.
- API still accepts legacy mapping_template.
- Conflicting dual inputs are rejected.
- OpenAPI includes mapping_rules.
- Example request uses mapping_rules.
```

---

# Phase 0 Task 0.3: Make Generic Candidate Mode Truly Domain-Neutral

## Problem

`Topic5ConversionService` already calls:

```python
CandidateService().extract_candidates(
    task_id,
    request.uir,
    candidate_profile=options.get("candidate_profile"),
    enable_legacy_domain_rules=False,
)
```

However, `CandidateService.extract_candidates()` still passes `uir.metadata.domain` into `_metadata_candidate_options()` even when legacy domain rules are disabled.

This means inline generic mode may still apply policy-specific metadata enrichment if `uir.metadata.domain == "policy_doc"`.

## Files to modify

```text
backend/app/services/candidate_service.py
backend/tests/test_candidate_service_generic_mode.py
```

## Required implementation

In `CandidateService.extract_candidates()`, change:

```python
semantic = self._metadata_candidate_options(
    str(uir.metadata.get("domain") or ""),
    key,
)
```

to:

```python
domain_for_metadata = (
    str(uir.metadata.get("domain") or "")
    if use_legacy_domain_rules
    else ""
)

semantic = self._metadata_candidate_options(
    domain_for_metadata,
    key,
)
```

Also make the special meeting attendee display alias conditional:

```python
display_name = semantic["display_name"] or (
    "attendees"
    if use_legacy_domain_rules
    and uir.metadata.get("domain") == "meeting_doc"
    and self.normalize_name(key) == "出席"
    else None
)
```

## Required tests

### Test 1: generic mode ignores policy metadata enrichment

Create UIR:

```python
uir.metadata = {
    "domain": "policy_doc",
    "issuer": "Some Office",
    "publishDate": "2026-07-09",
}
```

Run:

```python
candidates = CandidateService().extract_candidates(
    "task_generic",
    uir,
    enable_legacy_domain_rules=False,
)
```

Expected:

```python
issuer_candidate = find_candidate(candidates, "$.metadata.issuer")
assert issuer_candidate.display_name is None
assert issuer_candidate.target_hints == []
assert issuer_candidate.evidence_type == "metadata"
```

### Test 2: legacy mode preserves policy metadata enrichment

Run:

```python
candidates = CandidateService().extract_candidates(
    "task_legacy",
    uir,
    enable_legacy_domain_rules=True,
)
```

Expected:

```python
issuer_candidate.display_name == "issuer"
assert "issuer" in issuer_candidate.target_hints
```

### Test 3: generic mode still supports candidate_profile

Run with:

```python
candidate_profile = {
    "labeled_values": {
        "issuer": ["发布单位"],
        "publish_date": ["发布日期"]
    }
}
```

Expected:

```python
assert any(c.evidence_type == "candidate_profile" for c in candidates)
assert any("issuer" in c.target_hints for c in candidates)
```

## Acceptance criteria

```text
- Generic mode ignores domain-specific metadata enrichment.
- Legacy mode remains backward compatible.
- Topic 5 inline conversion still maps announcement_doc correctly through explicit mapping_rules and candidate_profile.
```

---

# Phase 0 Task 0.4: Add Configurable Built-in Router Signals

## Problem

`SchemaRouterService` still includes hard-coded built-in signals for five historical schema families.

This is acceptable as compatibility fallback, but the project must be able to run Router in a config-only mode.

## Files to modify

```text
backend/app/services/schema_router_service.py
backend/app/config.py
backend/tests/test_schema_router_config_driven.py
docs/external_uir_integration.md
docs/交接/requirement_mapping.md
```

## Required behavior

Support both modes:

```text
include_builtin_signals = true
  -> built-in historical signals + schema_pack router rules

include_builtin_signals = false
  -> only schema_pack router rules
```

Default should be `true` to avoid breaking existing tests and demos.

## Required implementation option A: constructor parameter

Modify class:

```python
class SchemaRouterService:
    def __init__(
        self,
        schema_pack_service: SchemaPackService | None = None,
        *,
        include_builtin_signals: bool = True,
    ) -> None:
        self.schema_pack_service = schema_pack_service or SchemaPackService()
        self.include_builtin_signals = include_builtin_signals
```

Modify `_signals()`:

```python
def _signals(self) -> dict[str, dict[str, Any]]:
    loaded = self.schema_pack_service.load_router_rules()

    if not self.include_builtin_signals:
        return loaded

    if not loaded:
        return self.SIGNALS

    merged = dict(self.SIGNALS)
    merged.update(loaded)
    return merged
```

If `include_builtin_signals=False` and `loaded` is empty, `route()` must not crash. Add a graceful decision:

```python
signals = self._signals()
if not signals:
    return SchemaRouteDecision(
        selected_schema_id=None,
        selected_template_id=None,
        confidence=0.0,
        reason="no schema router rules configured",
        decision_reason="no schema router rules configured",
        alternatives=[],
        review_required=True,
        candidates=[],
        route_version=self.ROUTE_VERSION,
    )
```

## Required tests

### Test 1: config-only mode uses announcement_doc router rules

```python
router = SchemaRouterService(include_builtin_signals=False)
decision = router.route(announcement_uir)
assert decision.selected_schema_id == "announcement_doc"
assert decision.candidates[0].source == "schema_pack_router_rules"
```

### Test 2: config-only mode returns review_required when no schema packs exist

Use a temporary empty schema pack root.

```python
service = SchemaPackService(root=tmp_path)
router = SchemaRouterService(
    schema_pack_service=service,
    include_builtin_signals=False,
)
decision = router.route(uir)
assert decision.selected_schema_id is None
assert decision.review_required is True
assert decision.confidence == 0.0
```

### Test 3: default mode remains backward compatible

```python
router = SchemaRouterService()
decision = router.route(procurement_uir)
assert decision.selected_schema_id is not None
```

## Acceptance criteria

```text
- Router can run with built-in signals disabled.
- Default behavior is backward compatible.
- Documentation clearly says Router is optional and only used for recommendation.
```

---

# Phase 0 Task 0.5: Clean Documentation Metric Contradictions

## Problem

Some documents contain stale metric statements from older stages. This can hurt defense credibility.

## Files to review and update

```text
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
docs/交接/final_demo_script.md
reports/topic5_alignment_gate_report.md
reports/topic5_alignment_gate_report.json
```

## Required documentation rules

Use these canonical statements:

```text
Canonical project positioning:
The system is a Topic 5 configuration-driven conversion agent. It accepts UIR, Target Schema, Metadata Template, Mapping Rules, and Content Organization Config.

SchemaPack positioning:
SchemaPack examples are reusable configuration assets and evaluation baselines, not system capability boundaries.

Mapping metric status:
Current strengthen-stage record:
- auto mapping recall: 0.812
- assisted mapping recall: 0.861
- dev assisted recall: 0.868
- test assisted recall: 0.868
- blind assisted recall: 0.884
- required missing: 0
- badcase violations: 0
- package verification: 50/50
- final status: conditional_pass

Production blind/shadow status:
No independent production shadow/blind UIR gold corpus has been completed. Do not claim production-grade blind recall 0.85.

LLM/Codex status:
LLM and Codex paths are report-only or dry-run. They do not auto-accept mappings, do not activate schema/template, and do not write production rules.
```

## Required edits

### README.md

Replace any stale test numbers with either:

```text
Latest full verification: rerun required after Topic 5 correction.
```

or update after running:

```text
Backend pytest: <new count> passed
OpenAPI paths: <new count>
Frontend tests: <new count> passed
```

Do not leave obsolete test counts unless they are still true after rerun.

### acceptance_report.md

Ensure these statements are not contradictory:

```text
Do not say both:
- assisted recall has reached 0.861
- current assisted recall is 0.809 and has not reached 0.85
```

Use:

```text
The historical basic-stage record did not reach 0.85.
The strengthen-stage record reached assisted recall 0.861.
The final status remains conditional_pass because auto recall is 0.812, review-required rate is 0.109, and independent production shadow/blind gold corpus is not available.
```

### requirement_mapping.md

Ensure DeepSeek unsafe suggestion count is consistent with the latest report being referenced. If uncertain, use:

```text
DeepSeek/LLM suggestion results are report-only and must be interpreted from the referenced stage report. No LLM mapping is auto-accepted or written to production rules.
```

## Required gate update

Update `scripts/check_topic5_alignment_gate.py` so it also checks that stale contradictions are absent.

Add forbidden phrases:

```python
FORBIDDEN_STALE_PHRASES = [
    "当前 50-sample 非采购语义评测 assisted recall 为 `0.8096514745`，尚未达到 0.85",
    "生产级盲测 0.85 已达成",
]
```

Then fail if any appear in docs.

## Acceptance criteria

```text
- README, acceptance_report, requirement_mapping, project_status, and demo script use one consistent Topic 5 positioning.
- No stale metric contradiction remains.
- Alignment gate checks stale contradiction phrases.
```

---

# Phase 0 Task 0.6: Re-run Verification and Regenerate Evidence

## Required commands

Run from repository root.

```powershell
# 1. Run Topic 5 inline demo with package generation
python scripts/run_topic5_inline_convert.py --create-package

# 2. Run Topic 5 correction alignment gate
python scripts/check_topic5_alignment_gate.py

# 3. Run backend full verification
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

# 4. Run frontend tests if frontend exists and dependencies are installed
Push-Location frontend
npm.cmd test
Pop-Location
```

If the project uses PowerShell scripts:

```powershell
.\scripts\run_basic_stage_verification.ps1
.\scripts\run_strengthen_stage_verification.ps1
```

Only run stage scripts if time allows. Phase 0 does not require recalculating all mapping benchmarks unless changes affect mapping logic broadly.

## Required report outputs

Update or regenerate:

```text
reports/topic5_inline_announcement_result.json
reports/topic5_alignment_gate_report.json
reports/topic5_alignment_gate_report.md
docs/openapi.json
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
README.md
```

## Acceptance criteria

```text
- topic5_inline_announcement_result.json status = passed
- package_verifier_passed = true
- topic5_alignment_gate_report status = passed
- verify_all passes
- OpenAPI contains /api/v1/topic5/convert and /api/v1/topic5/convert/package
```

---

# Phase 0 Final Checklist

Before merging Phase 0, verify:

```text
[ ] Topic5ConversionService final status checks mapping review, required unmapped, validation, and verifier.
[ ] Topic5ConvertRequest accepts mapping_rules.
[ ] Topic5ConvertRequest still accepts mapping_template.
[ ] Conflicting mapping_rules and mapping_template are rejected.
[ ] Generic candidate mode does not use domain-specific metadata logic.
[ ] Router built-in signals are configurable.
[ ] Documentation metrics are consistent.
[ ] Alignment gate checks for stale contradiction phrases.
[ ] Inline announcement demo passes.
[ ] Package verifier passes.
[ ] verify_all passes.
[ ] docs/openapi.json is regenerated.
```

Recommended merge commit:

```text
fix: harden topic5 inline correction gates
```

---

# Phase 1: Topic 5 Mainline Contract Solidification

## Phase 1 Goal

Turn the corrected Topic 5 mainline into a stable, well-documented, repeatable contract that Codex, teachers, and future maintainers can understand without reading the whole codebase.

After Phase 1, the project should be able to claim:

```text
Topic 5 conversion has a formal v1 input/output contract.
Mapping Rules are explicitly defined as the external task input.
MappingTemplate is only the internal model representation.
At least two no-code SchemaPack demos pass.
Inline config mode and registered SchemaPack mode are both documented.
```

---

## Phase 1 Scope

### In scope

- Create formal Topic 5 API contract documentation.
- Formalize `mapping_rules` semantics.
- Add one additional no-code SchemaPack demo.
- Add a SchemaPack onboarding checklist.
- Add tests proving no core-code change is required for a new SchemaPack.
- Improve CLI documentation and reproducibility.
- Update demo script and handoff docs.

### Out of scope

- Do not implement full global assignment yet.
- Do not build a front-end workbench yet.
- Do not introduce quality rules engine yet.
- Do not change Package 1.1 artifact contract unless needed.
- Do not attempt to prove auto mapping recall 0.85 in Phase 1.

---

## Phase 1 Branching Recommendation

Start from the hardened correction branch:

```powershell
git checkout fix/topic5-config-driven-correction
git pull
git checkout -b feat/topic5-config-contract
```

Recommended commit message:

```text
feat: formalize topic5 config contract
```

---

# Phase 1 Task 1.1: Create Topic 5 Convert API Contract Document

## Files to create

```text
docs/topic5_convert_api.md
```

## Required content

The document must be in English and must contain the following sections:

```text
# Topic 5 Convert API Contract

## 1. Purpose
## 2. Runtime Boundary
## 3. Input Contract
## 4. Output Contract
## 5. Mapping Rules Semantics
## 6. Content Organization Semantics
## 7. Status Semantics
## 8. Error Semantics
## 9. Example Request
## 10. Example Response
## 11. Package Generation Mode
## 12. Security and LLM Policy
## 13. Versioning Policy
## 14. Non-goals
```

## Required statements

### Purpose

Include:

```text
The Topic 5 Convert API is the canonical runtime entry point for the coursework Topic 5 data format standardization conversion agent.
```

### Runtime boundary

Include:

```text
The API starts from normalized UIR or External UIR converted into standard UIR. It does not parse raw PDF, Word, Excel, images, or scanned documents in production runtime.
```

### Input contract

Document these fields:

```text
uir
target_schema
metadata_template
mapping_rules
content_organization
options
```

Mention:

```text
mapping_template is accepted only as a backward-compatible alias for mapping_rules.
```

### Output contract

Document:

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

### Status semantics

Use exactly:

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

### LLM policy

Include:

```text
LLM assistance is disabled by default. If enabled in future extensions, it must remain report-only unless a separate explicit governance workflow accepts the result. LLM output must not directly activate schema, template, mapping rules, or production catalog entries.
```

## Acceptance criteria

```text
- docs/topic5_convert_api.md exists.
- It describes the exact request and response contract.
- It explains mapping_rules vs mapping_template.
- It explains status semantics.
- It clearly states runtime non-goals.
```

---

# Phase 1 Task 1.2: Define Mapping Rules Semantics

## Problem

The project currently uses `MappingTemplate` as the internal Pydantic model, but external project language should be `mapping_rules`.

## Files to create or update

```text
docs/mapping_rules_contract.md
docs/topic5_convert_api.md
schema_packs/README.md
schema_packs/schema_pack_contract.schema.json
```

## Required external concept

Define `mapping_rules` as:

```text
mapping_rules is the external configuration input that tells the Topic 5 conversion agent how to align source UIR candidates to target schema fields and how to transform mapped values.
```

## Required sections

```text
# Mapping Rules Contract

## 1. Overview
## 2. Required Identifiers
## 3. Field Aliases
## 4. Regex Rules
## 5. Transform Rules
## 6. Defaults
## 7. Enum Maps
## 8. Negative Pairs
## 9. Thresholds
## 10. Candidate Hints
## 11. Internal Model Compatibility
## 12. Examples
```

## Required mapping rules structure

Document this canonical structure:

```yaml
schema_id: announcement_doc
template_id: announcement_doc_base_v1
version: 1.0.0

aliases:
  title:
    - 标题
    - 公告标题
    - document_title

regex_rules:
  - target_field_id: publish_date
    pattern: "(?:发布日期|发布时间)\\s*[:：]\\s*(\\d{4}-\\d{1,2}-\\d{1,2})"
    group: 1
    confidence: 0.85

negative_pairs:
  - source_pattern: "抓取时间|retrieved_at"
    target_field_id: publish_date
    reason: "retrieved time is not publish date"
    severity: block

transform_rules:
  - rule_id: normalize_publish_date
    operation: normalize_date
    target_field_id: publish_date

defaults:
  body: ""

thresholds:
  auto_accept: 0.82
  review_required: 0.62

candidate_hints:
  labeled_values:
    issuer:
      - 发布单位
```

## Internal compatibility statement

Include:

```text
In the current backend implementation, mapping_rules are loaded into the MappingTemplate model for validation and execution. MappingTemplate is an internal compatibility model; the public Topic 5 concept is mapping_rules.
```

## Acceptance criteria

```text
- mapping_rules is documented as the external concept.
- MappingTemplate is documented as the internal model.
- negative_pairs and candidate_hints are documented.
- announcement_doc mapping_rules.yaml conforms to the documented structure.
```

---

# Phase 1 Task 1.3: Add a Second No-code SchemaPack Demo

## Purpose

The current `announcement_doc` demo is useful, but a single demo may look tailored. Add a second no-code SchemaPack to prove generality.

## Recommended SchemaPack

Use:

```text
event_notice_doc
```

Reason: it is simple, different from announcement_doc, and naturally includes title, organizer, event_time, location, audience, body.

## Files to create

```text
schema_packs/examples/event_notice_doc/target_schema.json
schema_packs/examples/event_notice_doc/metadata_template.json
schema_packs/examples/event_notice_doc/mapping_rules.yaml
schema_packs/examples/event_notice_doc/content_org.yaml
schema_packs/examples/event_notice_doc/router_rules.yaml

examples/topic5_inline/event_notice_uir.json
examples/topic5_inline/event_notice_convert_request.json

reports/topic5_inline_event_notice_result.json
```

## Target schema

Required fields:

```text
title          string required
organizer      string required
event_time     datetime required
location       string optional
audience       string optional
body           text required
```

Example target schema:

```json
{
  "schema_id": "event_notice_doc",
  "version": "1.0.0",
  "name": "Event Notice Document",
  "description": "Example target schema for no-code event notice onboarding.",
  "fields": [
    {
      "field_id": "title",
      "name": "title",
      "display_name": "活动标题",
      "type": "string",
      "required": true,
      "aliases": ["标题", "活动标题", "通知标题"],
      "constraints": {}
    },
    {
      "field_id": "organizer",
      "name": "organizer",
      "display_name": "主办单位",
      "type": "string",
      "required": true,
      "aliases": ["主办单位", "组织单位", "举办单位"],
      "constraints": {}
    },
    {
      "field_id": "event_time",
      "name": "event_time",
      "display_name": "活动时间",
      "type": "datetime",
      "required": true,
      "aliases": ["活动时间", "举办时间", "会议时间"],
      "constraints": {}
    },
    {
      "field_id": "location",
      "name": "location",
      "display_name": "活动地点",
      "type": "string",
      "required": false,
      "aliases": ["活动地点", "地点", "举办地点"],
      "constraints": {}
    },
    {
      "field_id": "audience",
      "name": "audience",
      "display_name": "参加对象",
      "type": "string",
      "required": false,
      "aliases": ["参加对象", "面向对象", "参与对象"],
      "constraints": {}
    },
    {
      "field_id": "body",
      "name": "body",
      "display_name": "正文",
      "type": "text",
      "required": true,
      "aliases": ["正文", "内容", "通知内容"],
      "constraints": {}
    }
  ]
}
```

## Example UIR

```json
{
  "uir_version": "1.0",
  "doc_id": "uir_event_notice_001",
  "metadata": {
    "source": "example",
    "language": "zh-CN",
    "document_title": "网络安全专题讲座通知"
  },
  "blocks": [
    {
      "block_id": "e1",
      "type": "heading",
      "level": 1,
      "text": "网络安全专题讲座通知",
      "attributes": {}
    },
    {
      "block_id": "e2",
      "type": "paragraph",
      "text": "主办单位：信息安全学院",
      "attributes": {}
    },
    {
      "block_id": "e3",
      "type": "paragraph",
      "text": "活动时间：2026-07-12 14:00",
      "attributes": {}
    },
    {
      "block_id": "e4",
      "type": "paragraph",
      "text": "活动地点：综合楼 301",
      "attributes": {}
    },
    {
      "block_id": "e5",
      "type": "paragraph",
      "text": "参加对象：全体信息安全专业学生",
      "attributes": {}
    },
    {
      "block_id": "e6",
      "type": "paragraph",
      "text": "请同学们提前十分钟入场，讲座将围绕零信任、数据治理和攻防实践展开。",
      "attributes": {
        "field_name": "正文"
      }
    }
  ],
  "assets": [],
  "normalization_records": []
}
```

## Required mapping rules

```yaml
schema_id: event_notice_doc
template_id: event_notice_doc_base_v1
version: 1.0.0

aliases:
  title:
    - 标题
    - 活动标题
    - 通知标题
    - document_title
  organizer:
    - 主办单位
    - 组织单位
    - 举办单位
  event_time:
    - 活动时间
    - 举办时间
    - 会议时间
  location:
    - 活动地点
    - 地点
    - 举办地点
  audience:
    - 参加对象
    - 面向对象
    - 参与对象
  body:
    - 正文
    - 内容
    - 通知内容

regex_rules:
  - target_field_id: event_time
    pattern: "(?:活动时间|举办时间|会议时间)\\s*[:：]\\s*(\\d{4}-\\d{1,2}-\\d{1,2}\\s+\\d{1,2}:\\d{2})"
    group: 1
    confidence: 0.85

negative_pairs:
  - source_pattern: "发布时间|发布日期|抓取时间|retrieved_at"
    target_field_id: event_time
    reason: "publish or retrieved time is not event time"
    severity: block

transform_rules:
  - rule_id: normalize_event_time
    operation: normalize_datetime
    target_field_id: event_time
  - rule_id: trim_title
    operation: trim
    target_field_id: title

defaults:
  location: ""

thresholds:
  auto_accept: 0.82
  review_required: 0.62

candidate_hints:
  labeled_values:
    organizer:
      - 主办单位
      - 组织单位
    event_time:
      - 活动时间
      - 举办时间
    location:
      - 活动地点
      - 地点
    audience:
      - 参加对象
```

## Script update

Use the existing script with explicit request and output:

```powershell
python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/event_notice_convert_request.json `
  --out reports/topic5_inline_event_notice_result.json `
  --create-package
```

No code change to `CandidateService` or `MappingService` is allowed for this demo.

## Required tests

Add:

```text
backend/tests/test_topic5_event_notice_no_code.py
```

Expected assertions:

```python
assert response.status == "completed"
assert response.schema_id == "event_notice_doc"
assert response.mapping_report["summary"]["required_unmapped_count"] == 0
assert response.mapping_report["summary"]["review_required_count"] == 0
assert response.validation_report["passed"] is True
```

Also assert no LLM:

```python
assert response.mapping_report["summary"].get("llm_suggestion_count", 0) == 0
```

## Acceptance criteria

```text
- event_notice_doc is fully implemented through config and fixtures.
- No CandidateService or MappingService code change is needed.
- event_notice inline conversion passes.
- package verifier passes.
- report is generated.
```

---

# Phase 1 Task 1.4: Add SchemaPack Onboarding Checklist

## Files to create

```text
docs/schema_pack_onboarding_checklist.md
```

## Required sections

```text
# SchemaPack Onboarding Checklist

## 1. Create SchemaPack Directory
## 2. Define Target Schema
## 3. Define Metadata Template
## 4. Define Mapping Rules
## 5. Define Content Organization Config
## 6. Optional Router Rules
## 7. Add Example UIR
## 8. Add Inline Convert Request
## 9. Run Inline Conversion
## 10. Run Package Verification
## 11. Add Badcases
## 12. Add Regression Test
## 13. Update Documentation
```

## Required checklist format

Use checkboxes:

```markdown
- [ ] `target_schema.json` defines `schema_id`, `version`, and non-empty `fields`.
- [ ] Required fields are truly required by downstream consumers.
- [ ] `mapping_rules.yaml` contains aliases for every required field.
- [ ] Negative pairs exist for known confusing fields.
- [ ] `content_org.yaml` defines chunk strategy and tag policy.
- [ ] At least one example UIR is provided.
- [ ] Inline conversion passes.
- [ ] Package verifier passes.
- [ ] No core backend code was modified for this SchemaPack.
```

## Acceptance criteria

```text
- A new contributor can follow the checklist to add a SchemaPack.
- Checklist explicitly says no core backend code should be modified for normal onboarding.
```

---

# Phase 1 Task 1.5: Add SchemaPack Contract Validation Script

## Purpose

Make SchemaPack configuration checkable and reproducible.

## Files to create

```text
scripts/validate_schema_pack.py
backend/tests/test_schema_pack_contract_validation.py
```

## Minimal validation requirements

The script accepts a SchemaPack directory:

```powershell
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc
```

It validates:

```text
target_schema.json exists and is valid TargetSchema
metadata_template.json exists and contains template_id/schema_id/version
mapping_rules.yaml exists and contains schema_id/template_id/version
content_org.yaml exists
router_rules.yaml exists or warning only
schema_id matches across files
template_id matches across files
required target fields have at least one alias or regex rule
negative_pairs entries have source_pattern and target_field_id
```

## Output JSON

Write to stdout:

```json
{
  "status": "passed",
  "schema_pack_id": "announcement_doc",
  "errors": [],
  "warnings": []
}
```

If failing:

```json
{
  "status": "failed",
  "schema_pack_id": "announcement_doc",
  "errors": [
    "mapping_rules.schema_id does not match target_schema.schema_id"
  ],
  "warnings": []
}
```

## Implementation note

The project currently has a simple YAML reader in `SchemaPackService`. For Phase 1, reuse it if acceptable.

If nested YAML parsing becomes unreliable, add a small dependency only if the project already allows it. Otherwise, keep the supported YAML subset simple and documented.

## Required tests

```python
def test_validate_announcement_schema_pack_passes():
    result = run_validator("schema_packs/examples/announcement_doc")
    assert result["status"] == "passed"


def test_validate_schema_pack_fails_on_missing_mapping_rules(tmp_path):
    copy_pack_without_mapping_rules(tmp_path)
    result = run_validator(tmp_path)
    assert result["status"] == "failed"
```

## Acceptance criteria

```text
- announcement_doc passes schema pack validation.
- event_notice_doc passes schema pack validation.
- invalid pack fails with clear error.
```

---

# Phase 1 Task 1.6: Update Demo Script and Handoff Documents

## Files to update

```text
docs/交接/final_demo_script.md
docs/交接/project_status.md
docs/交接/requirement_mapping.md
docs/交接/acceptance_report.md
README.md
```

## Required demo narrative

The demo must follow this order:

```text
1. Show Topic 5 expected input model.
2. Show inline request: UIR + target_schema + mapping_rules + metadata_template + content_organization.
3. Run /api/v1/topic5/convert/package or CLI equivalent.
4. Show content.json.
5. Show content.md.
6. Show chunks and content_organization_report.
7. Show mapping_report evidence.
8. Show validation_report.
9. Show manifest and verifier_report.
10. Show no-code SchemaPack onboarding demo.
11. Explain that historical schema packs are examples, not capability boundaries.
12. Explain current honest limitations.
```

## Required limitation statements

Include:

```text
The project does not parse raw PDF, Word, Excel, images, or scanned documents in production runtime.
The project does not claim production-grade blind recall 0.85.
The current stronger mapping metric is assisted recall 0.861, while auto recall still needs improvement.
LLM and Codex paths are report-only or dry-run and do not write production rules.
```

## Acceptance criteria

```text
- Demo script no longer starts from SchemaPack platform features.
- Demo script starts from Topic 5 input/output contract.
- Limitations are clear and consistent.
```

---

# Phase 1 Task 1.7: Regenerate OpenAPI and Evidence Reports

## Required commands

```powershell
# 1. Validate SchemaPacks
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc
python scripts/validate_schema_pack.py schema_packs/examples/event_notice_doc

# 2. Run inline demos
python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/announcement_convert_request.json `
  --out reports/topic5_inline_announcement_result.json `
  --create-package

python scripts/run_topic5_inline_convert.py `
  --request examples/topic5_inline/event_notice_convert_request.json `
  --out reports/topic5_inline_event_notice_result.json `
  --create-package

# 3. Run correction alignment gate
python scripts/check_topic5_alignment_gate.py

# 4. Run full backend verification and OpenAPI export
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi

# 5. Run frontend tests if dependencies exist
Push-Location frontend
npm.cmd test
Pop-Location
```

## Reports to update

```text
reports/topic5_inline_announcement_result.json
reports/topic5_inline_event_notice_result.json
reports/topic5_alignment_gate_report.json
reports/topic5_alignment_gate_report.md
docs/openapi.json
README.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
docs/交接/project_status.md
```

## Acceptance criteria

```text
- Both no-code demos pass.
- Both packages pass verifier.
- Alignment gate passes.
- Full backend verification passes.
- Documentation references current regenerated evidence.
```

---

# Phase 1 Final Checklist

Before merging Phase 1, verify:

```text
[ ] docs/topic5_convert_api.md exists.
[ ] docs/mapping_rules_contract.md exists.
[ ] docs/schema_pack_onboarding_checklist.md exists.
[ ] mapping_rules is the preferred public API term.
[ ] mapping_template remains backward compatible.
[ ] announcement_doc no-code demo passes.
[ ] event_notice_doc no-code demo passes.
[ ] validate_schema_pack.py validates both packs.
[ ] final_demo_script starts from Topic 5 input/output contract.
[ ] acceptance_report has no stale contradictions.
[ ] OpenAPI regenerated.
[ ] verify_all passes.
```

Recommended merge commit:

```text
feat: formalize topic5 config contract
```

---

# Combined Phase 0 + Phase 1 Acceptance Gate

The project can be considered corrected and ready for the next improvement stage only if all of the following are true:

```text
[ ] Topic 5 inline API accepts UIR + target_schema + mapping_rules + metadata_template + content_organization.
[ ] mapping_template is backward compatible but no longer the primary public term.
[ ] Generic candidate extraction does not rely on built-in domain rules in inline Topic 5 mode.
[ ] Router can run in config-only mode.
[ ] At least two no-code SchemaPack demos pass.
[ ] Package verifier passes for both demos.
[ ] SchemaPack onboarding is documented.
[ ] SchemaPack validation script exists.
[ ] Documentation clearly says SchemaPack examples are not system capability boundaries.
[ ] Documentation does not claim production-grade blind 0.85.
[ ] LLM/Codex paths remain report-only or dry-run.
[ ] Full verification passes.
```

---

# Recommended Final Branch Structure

```text
fix/topic5-inline-hardening
  -> Phase 0 only

feat/topic5-config-contract
  -> Phase 1 only

main
  -> merge Phase 0 first
  -> merge Phase 1 second
```

Do not mix Phase 2 mapping algorithm changes into Phase 0 or Phase 1.

---

# Next Stage After Phase 1

After Phase 1 is merged, proceed to Phase 2:

```text
Phase 2: Automatic Mapping Improvement
```

Recommended Phase 2 order:

```text
1. Add standard UIR mapping benchmark.
2. Add precision / recall / F1 / review-rate evaluator.
3. Add blind split and no-gold-leak guard.
4. Replace per-target greedy mapping with global assignment.
5. Add value validators and stronger negative-pair regression.
6. Target auto recall >= 0.85 on declared supported scope.
```
