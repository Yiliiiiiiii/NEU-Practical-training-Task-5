# Phase 2 Execution Plan: Automatic Mapping Improvement

Version: 1.0  
Target branch recommendation: `feat/topic5-mapping-benchmark` then `feat/topic5-global-assignment`  
Base branch recommendation: merge or rebase from `fix/topic5-inline-hardening` after Phase 0/1 acceptance  
Primary objective: improve Topic 5 automatic field mapping from a configuration-driven demo into a measurable, regression-protected mapping system.

---

## 1. Phase 2 Goal

Phase 0 and Phase 1 corrected the project positioning:

```text
UIR
+ Target Schema
+ Metadata Template
+ Mapping Rules
+ Content Organization Config
-> Standard Topic 5 package
```

Phase 2 focuses on the mapping quality itself.

The goal is to move from:

```text
assisted mapping success
```

toward:

```text
auto mapping success with measurable precision / recall / F1 on declared benchmark splits
```

The recommended target is:

```text
auto_mapping_recall >= 0.85
auto_mapping_precision >= 0.90
required_unmapped_count = 0
badcase_violations = 0
review_required_rate <= 0.08
test_vs_blind_gap <= 0.03
```

Do not claim production-grade arbitrary-schema matching. The target scope must be explicitly declared:

```text
Standard UIR inputs
+ registered or inline target schemas
+ declared mapping_rules
+ benchmarked document families
+ no gold leakage
```

---

## 2. Why Phase 2 Is Needed

The current project already supports configuration-driven conversion, no-code SchemaPack demos, inline Topic 5 conversion, mapping reports, validation reports, and verified packages.

However, the existing mapping algorithm is still mainly sequential:

```text
for each target field:
    exact
    alias
    regex
    evidence_ranked
    type
    fuzzy / llm fallback review
```

This is acceptable for coursework demonstration, but it has limitations:

1. A source candidate may be consumed by an earlier target even if it is better suited for a later target.
2. Confidence is calculated per field, not as a global assignment problem.
3. Evaluation is not yet centered on an independent Topic 5 standard UIR benchmark.
4. Current mapping quality metrics mix assisted and automatic results.
5. Review-required cases are useful, but the next improvement goal is to reduce review rate while preserving precision.

Phase 2 fixes these limitations in a controlled way.

---

## 3. External References and Design Principles

Phase 2 should follow these ideas:

### 3.1 Benchmark-first development

Valentine is an open-source schema matching experiment suite designed to organize large-scale automated matching experiments with datasets, ground truth, reference implementations, and evaluation metrics. Phase 2 should adopt the same idea at coursework scale: benchmark first, algorithm second.

### 3.2 Schema matching is not fully automatic in the general case

Schema matching is fundamentally difficult because semantics may differ or be undocumented. Therefore, this project should not claim universal automatic matching. It should claim measurable automatic matching within a declared scope.

### 3.3 Global assignment is better than local greedy matching

Schema matching can be modeled as assigning source candidates to target fields. A global assignment strategy avoids simple sequential mistakes. The Hungarian algorithm is a classic polynomial-time method for the assignment problem, but Phase 2 can start with a simpler global greedy assignment and leave Hungarian assignment as an optional later step.

### 3.4 Retrieval-enhanced LLM matching should remain gated

ReMatch shows that retrieval-enhanced LLMs can help schema matching without requiring training data. However, this project should keep LLM output report-only or top-k rerank-only. LLM results must not directly activate mapping rules or auto-accept mappings.

---

## 4. Phase 2 Work Breakdown

Phase 2 is divided into five sprints:

```text
Sprint 2.1: Topic 5 Standard UIR Mapping Benchmark
Sprint 2.2: Pair Feature Builder and Pair Scoring
Sprint 2.3: Global Assignment Mapper
Sprint 2.4: Validation-driven Repair and Negative Regression
Sprint 2.5: Final Auto Mapping 0.85 Gate and Documentation
```

Each sprint should be implemented as a separate commit or branch.

---

# Sprint 2.1: Topic 5 Standard UIR Mapping Benchmark

## 4.1 Goal

Create an independent benchmark for Topic 5 mapping quality.

The benchmark must measure:

```text
auto precision
auto recall
auto F1
assisted recall
review-required rate
required unmapped count
badcase violations
split gap
package pass rate
```

This sprint should not change mapping algorithms yet. It creates the evaluation foundation.

---

## 4.2 Files and Directories to Add

```text
eval/topic5_standard_uir/
  README.md
  manifest.jsonl
  splits/
    dev.json
    test.json
    blind.json
  uir/
    announcement_doc/
    event_notice_doc/
    policy_doc/
    meeting_doc/
    procurement_doc/
    general_doc/
  gold/
    mapping_gold.jsonl
    negative_pairs.jsonl
    required_fields.json
  reports/
    .gitkeep

scripts/eval_topic5_standard_uir_mapping.py
backend/tests/test_topic5_standard_uir_eval.py
```

Optional helper files:

```text
scripts/build_topic5_standard_uir_fixture.py
backend/app/services/topic5_mapping_eval_service.py
```

---

## 4.3 Dataset Scope

Minimum recommended dataset:

```text
announcement_doc: 10 samples
event_notice_doc: 10 samples
policy_doc: 10 samples
meeting_doc: 10 samples
procurement_doc: 10 samples
general_doc: 10 samples
```

Minimum total:

```text
60 UIR samples
```

Better target:

```text
120 UIR samples
```

Do not use only the two no-code demos. That would overfit to the correction examples.

---

## 4.4 Split Rules

Use family-aware splits. Do not randomly split fields from the same source template.

Required files:

```text
eval/topic5_standard_uir/splits/dev.json
eval/topic5_standard_uir/splits/test.json
eval/topic5_standard_uir/splits/blind.json
```

Example:

```json
{
  "split": "dev",
  "items": [
    "announcement_doc/ann_001.json",
    "event_notice_doc/event_001.json"
  ]
}
```

Rules:

```text
dev:
  used for tuning thresholds and feature weights

test:
  used for regression checks after algorithm changes

blind:
  must not be used while editing rules or weights
```

---

## 4.5 Gold Mapping Format

Create:

```text
eval/topic5_standard_uir/gold/mapping_gold.jsonl
```

Each line:

```json
{
  "doc_id": "uir_event_notice_001",
  "schema_id": "event_notice_doc",
  "target_field_id": "event_time",
  "source_path": "$.blocks.e3.text",
  "source_name": "event time",
  "required": true,
  "match_type": "exact",
  "notes": "event time explicitly labeled in source block"
}
```

Allowed `match_type`:

```text
exact
alias
regex
derived
aggregate
default
manual_review_expected
```

---

## 4.6 Negative Pair Format

Create:

```text
eval/topic5_standard_uir/gold/negative_pairs.jsonl
```

Each line:

```json
{
  "schema_id": "event_notice_doc",
  "source_pattern": "publish date|retrieved_at",
  "target_field_id": "event_time",
  "reason": "publish or retrieved time is not event time",
  "severity": "block"
}
```

---

## 4.7 Required Fields Format

Create:

```text
eval/topic5_standard_uir/gold/required_fields.json
```

Example:

```json
{
  "announcement_doc": ["title", "body"],
  "event_notice_doc": ["title", "organizer", "event_time", "body"],
  "policy_doc": ["title", "issuer", "publish_date"],
  "meeting_doc": ["title", "meeting_date"],
  "procurement_doc": ["project_name", "purchaser"],
  "general_doc": ["title", "body"]
}
```

Adjust field IDs to match actual schemas.

---

## 4.8 Evaluator Script

Create:

```text
scripts/eval_topic5_standard_uir_mapping.py
```

Required CLI:

```powershell
python scripts/eval_topic5_standard_uir_mapping.py `
  --dataset eval/topic5_standard_uir `
  --split dev `
  --out reports/topic5_standard_uir_mapping_dev.json `
  --markdown reports/topic5_standard_uir_mapping_dev.md
```

Support:

```text
--split dev
--split test
--split blind
--split all
--fail-on-gate
--auto-recall-threshold 0.85
--auto-precision-threshold 0.90
--review-rate-threshold 0.08
```

---

## 4.9 Evaluation Logic

For each UIR item:

1. Load UIR.
2. Load target schema and mapping rules.
3. Run Topic 5 conversion in memory.
4. Extract accepted mappings from `mapping_report.mappings`.
5. Extract review-required mappings from `mapping_report.review_required_items`.
6. Compare accepted mappings against gold.
7. Calculate metrics.

### Definitions

```text
auto_tp:
  accepted mapping source_path and target_field_id match gold

auto_fp:
  accepted mapping target_field_id is not in gold
  or accepted source_path differs from gold

auto_fn:
  gold mapping target_field_id not accepted automatically

assisted_tp:
  accepted or review-required mapping supports the gold target field

badcase_violation:
  accepted mapping violates a negative pair

required_missing:
  required target field has neither accepted nor review-supported mapping
```

### Metrics

```python
auto_precision = auto_tp / max(auto_tp + auto_fp, 1)
auto_recall = auto_tp / max(auto_tp + auto_fn, 1)
auto_f1 = 2 * precision * recall / max(precision + recall, 1e-9)
assisted_recall = assisted_tp / max(total_gold, 1)
review_required_rate = review_required_count / max(total_target_fields, 1)
```

### Split gap

```python
split_gap = abs(test_auto_recall - blind_auto_recall)
```

Gate:

```text
split_gap <= 0.03
```

---

## 4.10 Report Format

JSON report:

```json
{
  "status": "passed",
  "split": "test",
  "dataset_size": 60,
  "metrics": {
    "auto_precision": 0.91,
    "auto_recall": 0.85,
    "auto_f1": 0.88,
    "assisted_recall": 0.90,
    "review_required_rate": 0.07,
    "required_missing": 0,
    "badcase_violations": 0,
    "package_pass_rate": 1.0
  },
  "by_schema": {
    "event_notice_doc": {
      "auto_precision": 1.0,
      "auto_recall": 0.95
    }
  },
  "failures": [],
  "badcases": []
}
```

Markdown report:

```markdown
# Topic 5 Standard UIR Mapping Evaluation

- split: test
- status: passed
- auto precision: 0.91
- auto recall: 0.85
- review-required rate: 0.07
- required missing: 0
- badcase violations: 0
```

---

## 4.11 Tests

Add:

```text
backend/tests/test_topic5_standard_uir_eval.py
```

Minimum tests:

```python
def test_eval_script_loads_dataset():
    ...

def test_eval_metrics_precision_recall():
    ...

def test_badcase_violation_detection():
    ...

def test_required_missing_detection():
    ...
```

---

## 4.12 Acceptance Criteria

```text
[ ] eval/topic5_standard_uir exists.
[ ] dev/test/blind split files exist.
[ ] mapping_gold.jsonl exists.
[ ] negative_pairs.jsonl exists.
[ ] evaluator script runs on dev split.
[ ] report contains auto_precision, auto_recall, auto_f1, assisted_recall, review_required_rate.
[ ] report separates accepted mappings from review-required mappings.
[ ] no algorithm changes are mixed into Sprint 2.1.
```

Recommended commit:

```text
test: add topic5 standard uir mapping benchmark
```

---

# Sprint 2.2: Pair Feature Builder and Pair Scoring

## 5.1 Goal

Create a reusable feature builder for source-target candidate pairs.

This sprint prepares for global assignment. It should not fully replace the existing mapper yet.

---

## 5.2 Files to Add

```text
backend/app/services/mapping_pair_feature_service.py
backend/app/schemas/mapping_features.py
backend/tests/test_mapping_pair_feature_service.py
```

Optional:

```text
backend/app/services/value_validator_service.py
backend/tests/test_value_validator_service.py
```

---

## 5.3 Data Model

Create `MappingPairFeatures`.

Example:

```python
class MappingPairFeatures(StrictBaseModel):
    source_candidate_id: str
    source_path: str
    source_name: str
    target_field_id: str
    target_name: str

    lexical_score: float
    alias_score: float
    type_score: float
    value_score: float
    path_score: float
    context_score: float
    evidence_score: float
    negative_score: float
    source_quality_score: float

    final_score: float
    reasons: list[str] = []
    risk_flags: list[str] = []
```

---

## 5.4 Required Features

### lexical_score

Compare:

```text
candidate.source_name
candidate.display_name
target.field_id
target.name
target.display_name
target.aliases
```

Use existing `SequenceMatcher` first. Optionally add RapidFuzz later.

### alias_score

```text
1.0 if exact normalized alias match
0.9 if candidate target_hints contains target field
0.0 otherwise
```

### type_score

Reuse or move existing `_type_score()` from `MappingService`.

### value_score

Add simple validators:

```text
date field:
  value looks like date -> 1.0
  value is text but contains date -> 0.7
  otherwise -> 0.2

datetime field:
  value looks like datetime -> 1.0
  date only -> 0.6

number field:
  numeric value or amount text -> 1.0
  otherwise -> 0.2

array field:
  list or newline/bullet text -> 1.0
```

### path_score

```text
1.0 if target field id appears in source path
0.8 if source path is metadata and target is metadata-like
0.7 if source block exists
0.4 otherwise
```

### context_score

Use available block text, title path, heading path, or nearby source text if available.

For Phase 2.2, implement simple version:

```text
0.9 if candidate.source_blocks not empty
0.75 if metadata
0.5 otherwise
```

### evidence_score

Move current evidence-type weights out of `MappingService._ranking_trace()` into a reusable mapping.

### negative_score

```text
1.0 if configured or built-in negative pair hits
0.0 otherwise
```

### source_quality_score

```text
1.0 source_path + source_blocks available
0.85 metadata path available
0.5 source_path only
0.0 missing source path
```

---

## 5.5 Final Score Formula

Start with:

```python
final_score = (
    lexical_score * 0.25
    + alias_score * 0.20
    + evidence_score * 0.20
    + type_score * 0.10
    + value_score * 0.10
    + path_score * 0.05
    + context_score * 0.05
    + source_quality_score * 0.05
    - negative_score * 1.0
)
```

Clamp:

```python
final_score = max(0.0, min(final_score, 1.0))
```

Keep weights configurable later, but hardcode for initial implementation.

---

## 5.6 Integration Requirement

Do not replace the existing mapper yet. Add optional debug output in mapping report only if low-risk.

Recommended:

```python
options.get("enable_pair_feature_trace", False)
```

If enabled, include:

```json
"pair_feature_trace": [
  {
    "source_candidate_id": "...",
    "target_field_id": "...",
    "final_score": 0.91,
    "features": {}
  }
]
```

---

## 5.7 Tests

Create tests for:

```text
exact alias match
date value match
negative pair block
type mismatch
metadata source quality
```

Example:

```python
def test_pair_feature_alias_match_scores_high():
    ...

def test_pair_feature_negative_pair_scores_zero():
    ...

def test_pair_feature_date_value_score():
    ...
```

---

## 5.8 Acceptance Criteria

```text
[ ] MappingPairFeatureService exists.
[ ] It calculates lexical, alias, type, value, path, context, evidence, negative, and source quality features.
[ ] Unit tests cover major feature types.
[ ] Existing conversion behavior remains unchanged by default.
```

Recommended commit:

```text
feat: add mapping pair feature builder
```

---

# Sprint 2.3: Global Assignment Mapper

## 6.1 Goal

Replace per-target sequential candidate selection with a global source-target assignment path, initially behind a feature flag.

---

## 6.2 Files to Add or Modify

```text
backend/app/services/global_assignment_mapping_service.py
backend/app/services/mapping_service.py
backend/app/services/topic5_conversion_service.py
backend/tests/test_global_assignment_mapping_service.py
backend/tests/test_topic5_global_assignment_eval.py
```

Optional:

```text
backend/app/schemas/global_assignment.py
```

---

## 6.3 Feature Flag

Add option:

```json
{
  "mapping_mode": "legacy"
}
```

Supported values:

```text
legacy
global_assignment
```

Default:

```text
legacy
```

In Topic 5 evaluator, support:

```powershell
--mapping-mode legacy
--mapping-mode global_assignment
```

---

## 6.4 Global Assignment Algorithm

Initial implementation: greedy global assignment.

### Step 1: Generate all pairs

```python
pairs = []
for target in schema.fields:
    for candidate in candidates:
        features = pair_feature_service.build(candidate, target, template, options)
        if features.final_score >= min_candidate_score:
            pairs.append((target, candidate, features))
```

### Step 2: Sort pairs

```python
pairs.sort(
    key=lambda p: (
        -p.features.final_score,
        -p.candidate.confidence,
        p.target.field_id,
        p.candidate.source_path,
    )
)
```

### Step 3: Accept without conflict

```python
used_targets = set()
used_sources = set()
accepted = []
review_required = []

for pair in pairs:
    if pair.target.field_id in used_targets:
        continue
    if pair.candidate.source_path in used_sources:
        continue

    if pair.features.negative_score >= 1.0:
        review_required.append(blocked_mapping(pair))
        used_targets.add(pair.target.field_id)
        continue

    if pair.features.final_score >= auto_accept_threshold:
        accepted.append(accepted_mapping(pair))
        used_targets.add(pair.target.field_id)
        used_sources.add(pair.candidate.source_path)
    elif pair.features.final_score >= review_threshold:
        review_required.append(review_mapping(pair))
        used_targets.add(pair.target.field_id)
```

### Step 4: Mark required unmapped

For required fields not in accepted or review-supported:

```python
unmapped.append(required_unmapped_item)
```

---

## 6.5 Optional Hungarian Assignment

Do not implement Hungarian assignment in the first PR unless simple greedy underperforms.

If added later:

```text
Build cost matrix = 1 - final_score
Use scipy.optimize.linear_sum_assignment if scipy already exists
Otherwise keep greedy fallback
```

Do not add heavy dependency just for this sprint unless allowed by project constraints.

---

## 6.6 Mapping Report Compatibility

The global assignment mapper must still return `MappingReport` with the same structure:

```text
summary
mappings
review_required_items
unmapped
```

Add to summary:

```json
{
  "mapping_mode": "global_assignment",
  "pair_count": 123,
  "conflict_skipped_count": 12,
  "auto_accept_threshold": 0.82,
  "review_threshold": 0.62
}
```

Each mapping should include:

```json
"ranking_trace": {
  "final_score": 0.91,
  "lexical_score": 0.88,
  "alias_score": 1.0,
  "type_score": 1.0,
  "value_score": 1.0
}
```

---

## 6.7 Integration Point

In `MappingService.map_fields()`:

```python
if options.get("mapping_mode") == "global_assignment":
    return GlobalAssignmentMappingService(...).map_fields(...)
```

Or in `Topic5ConversionService`, select mapper before calling.

Recommended low-risk path:

```python
mapping_report = MappingService(...).map_fields(...)
```

Inside `MappingService.map_fields()`, delegate if mode is enabled.

---

## 6.8 Tests

Required tests:

```text
1. global assignment prevents wrong early source consumption
2. required unmapped fields are reported
3. negative pair is blocked
4. review threshold creates review_required item
5. legacy mode remains unchanged
6. Topic5 conversion works with mapping_mode=global_assignment
```

Example conflict case:

```text
Source candidates:
  "publish date" -> 2026-07-09
  "event date" -> 2026-07-12

Targets:
  publish_date
  event_time

Expected:
  event date maps to event_time
  publish date does not steal event_time
```

---

## 6.9 Evaluation

Run:

```powershell
python scripts/eval_topic5_standard_uir_mapping.py `
  --dataset eval/topic5_standard_uir `
  --split dev `
  --mapping-mode legacy `
  --out reports/topic5_standard_uir_legacy_dev.json `
  --markdown reports/topic5_standard_uir_legacy_dev.md

python scripts/eval_topic5_standard_uir_mapping.py `
  --dataset eval/topic5_standard_uir `
  --split dev `
  --mapping-mode global_assignment `
  --out reports/topic5_standard_uir_global_dev.json `
  --markdown reports/topic5_standard_uir_global_dev.md
```

Compare:

```text
auto precision
auto recall
review_required_rate
badcase violations
required missing
```

---

## 6.10 Acceptance Criteria

```text
[ ] Global assignment mode exists behind feature flag.
[ ] Legacy mode remains default.
[ ] Global assignment report is compatible with MappingReport.
[ ] Conflict tests pass.
[ ] Dev split report shows no precision regression.
[ ] Required unmapped and badcase violation metrics remain safe.
```

Recommended commit:

```text
feat: add global assignment mapping mode
```

---

# Sprint 2.4: Validation-driven Repair and Negative Regression

## 7.1 Goal

Use validation failures and negative pair failures to attempt safe second-pass repair.

This is not LLM repair. It is deterministic.

---

## 7.2 Files to Add or Modify

```text
backend/app/services/mapping_repair_service.py
backend/app/services/topic5_conversion_service.py
backend/app/services/task_execution_service.py
backend/tests/test_mapping_repair_service.py
scripts/eval_topic5_standard_uir_mapping.py
```

---

## 7.3 Repair Strategy

### First pass

Run mapping normally.

### Validate

Run transform and validation.

### If failure

For each failed field:

```text
type mismatch
required missing
negative pair blocked
value validator failed
```

try next-best candidate from pair feature trace.

### Limits

```text
max_repair_rounds = 2
do not repair if confidence below review threshold
do not repair if negative pair hits
do not use LLM
do not modify mapping_rules automatically
```

---

## 7.4 Repair Report

Add:

```text
mapping_repair_report.json
```

Initially keep it as task report, not required Package 1.1 artifact.

Example:

```json
{
  "enabled": true,
  "rounds": 1,
  "attempted_fields": ["publish_date"],
  "repaired_fields": ["publish_date"],
  "unrepaired_fields": [],
  "blocked_candidates": [
    {
      "target_field_id": "publish_date",
      "candidate_id": "cand_x",
      "reason": "configured_negative_pair"
    }
  ]
}
```

---

## 7.5 Negative Regression Tests

Add dataset cases for common confusions:

```text
publish_date -> effective_date
retrieved_at -> publish_date
budget_amount -> award_amount
host -> attendees
contact -> service_object
publish_date -> event_time
```

Each case should assert:

```text
badcase_violations = 0
blocked mapping is not accepted
```

---

## 7.6 Acceptance Criteria

```text
[ ] Repair is deterministic and limited.
[ ] Repair never accepts negative-pair candidates.
[ ] Repair improves required_missing or validation pass rate on dev.
[ ] Repair does not reduce precision on test.
[ ] Repair report is generated when enabled.
```

Recommended commit:

```text
feat: add validation-driven mapping repair
```

---

# Sprint 2.5: Final Auto Mapping 0.85 Gate and Documentation

## 8.1 Goal

Create final Phase 2 evidence and gate.

---

## 8.2 Files to Create or Update

```text
scripts/check_topic5_mapping_quality_gate.py
reports/topic5_mapping_quality_gate_report.json
reports/topic5_mapping_quality_gate_report.md
docs/交接/topic5_mapping_quality_phase2.md
docs/交接/acceptance_report.md
docs/交接/requirement_mapping.md
README.md
```

---

## 8.3 Quality Gate Script

Create:

```text
scripts/check_topic5_mapping_quality_gate.py
```

Required behavior:

```powershell
python scripts/check_topic5_mapping_quality_gate.py `
  --dataset eval/topic5_standard_uir `
  --mode global_assignment `
  --fail-on-gate
```

Gate thresholds:

```text
auto_precision >= 0.90
auto_recall >= 0.85
required_missing = 0
badcase_violations = 0
review_required_rate <= 0.08
test_vs_blind_gap <= 0.03
```

If not met, script must still write report but exit non-zero only when `--fail-on-gate` is passed.

---

## 8.4 Gate Report

JSON:

```json
{
  "status": "passed",
  "mode": "global_assignment",
  "thresholds": {
    "auto_precision": 0.90,
    "auto_recall": 0.85,
    "review_required_rate": 0.08,
    "test_vs_blind_gap": 0.03
  },
  "actual": {
    "dev": {},
    "test": {},
    "blind": {}
  },
  "failed_checks": []
}
```

Markdown:

```markdown
# Topic 5 Mapping Quality Gate

- status: passed
- mode: global_assignment
- auto recall: 0.85
- auto precision: 0.90
- review-required rate: 0.07
- required missing: 0
- badcase violations: 0
- test vs blind gap: 0.02
```

---

## 8.5 Documentation Rules

If gate passes:

```text
The project can claim Topic 5 benchmark-level auto mapping recall >= 0.85 within the declared standard UIR benchmark scope.
```

If gate does not pass:

```text
The project must not claim auto mapping recall >= 0.85.
It may claim benchmark infrastructure is ready and report the current measured value.
```

Always include:

```text
This is not a production shadow/blind claim unless production_shadow_eval_report.json is also completed.
```

---

## 8.6 Acceptance Criteria

```text
[ ] check_topic5_mapping_quality_gate.py exists.
[ ] dev/test/blind reports are generated.
[ ] final gate report is generated.
[ ] documentation uses measured metrics only.
[ ] no production-grade claim is made unless production shadow/blind corpus exists.
```

Recommended commit:

```text
test: add topic5 mapping quality gate
```

---

# 9. Phase 2 Final Verification Commands

Run all commands from repository root.

```powershell
# Phase 2 benchmark
python scripts/eval_topic5_standard_uir_mapping.py `
  --dataset eval/topic5_standard_uir `
  --split all `
  --mapping-mode legacy `
  --out reports/topic5_standard_uir_legacy_all.json `
  --markdown reports/topic5_standard_uir_legacy_all.md

python scripts/eval_topic5_standard_uir_mapping.py `
  --dataset eval/topic5_standard_uir `
  --split all `
  --mapping-mode global_assignment `
  --out reports/topic5_standard_uir_global_all.json `
  --markdown reports/topic5_standard_uir_global_all.md

# Phase 2 quality gate
python scripts/check_topic5_mapping_quality_gate.py `
  --dataset eval/topic5_standard_uir `
  --mode global_assignment

# Topic 5 correction gate
python scripts/check_topic5_alignment_gate.py

# Existing verification
backend\.venv\Scripts\python.exe scripts\verify_all.py --check-openapi
```

Optional:

```powershell
Push-Location frontend
npm.cmd test
Pop-Location
```

---

# 10. Phase 2 Final Acceptance Checklist

```text
[ ] Standard UIR benchmark exists.
[ ] dev/test/blind splits exist.
[ ] mapping gold exists.
[ ] negative pair gold exists.
[ ] evaluator reports precision/recall/F1.
[ ] legacy mapping baseline report exists.
[ ] global assignment report exists.
[ ] global assignment mode is feature-flagged.
[ ] default runtime remains backward compatible.
[ ] negative pair regression passes.
[ ] required_missing = 0 on target gate split.
[ ] badcase_violations = 0 on target gate split.
[ ] documentation does not overclaim production performance.
```

---

# 11. Recommended Branch and Commit Structure

Use small branches:

```text
feat/topic5-mapping-benchmark
feat/topic5-pair-features
feat/topic5-global-assignment
feat/topic5-mapping-repair
feat/topic5-mapping-quality-gate
```

Recommended merge order:

```text
1. feat/topic5-mapping-benchmark
2. feat/topic5-pair-features
3. feat/topic5-global-assignment
4. feat/topic5-mapping-repair
5. feat/topic5-mapping-quality-gate
```

---

# 12. What Not to Do in Phase 2

Do not:

```text
- hardcode gold answers into CandidateService
- tune thresholds on blind split
- count review_required mappings as automatic mappings
- claim production-grade 0.85 without production shadow/blind corpus
- allow LLM to auto-accept mappings
- activate schema/template/rules from LLM output
- break existing Package 1.1 contract
- remove legacy mode before global_assignment is proven stable
```

---

# 13. Phase 2 Success Statement

If Phase 2 passes, use this statement:

```text
Phase 2 establishes an independent Topic 5 standard UIR mapping benchmark and introduces a feature-flagged global assignment mapper. Within the declared benchmark scope, the system reports automatic precision, recall, F1, review-required rate, required missing count, and badcase violations separately. If the quality gate passes, the project may claim benchmark-level auto mapping recall >= 0.85, while still avoiding any unsupported production-grade blind recall claim.
```
