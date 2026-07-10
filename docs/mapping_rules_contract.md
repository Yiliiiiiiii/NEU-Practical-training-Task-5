# Mapping Rules Contract

## 1. Overview

`mapping_rules` is the external configuration input that tells the Topic 5 conversion agent how to align source UIR candidates to target schema fields and how to transform mapped values.

In the current backend implementation, `mapping_rules` are loaded into the `MappingTemplate` model for validation and execution. `MappingTemplate` is an internal compatibility model; the public Topic 5 concept is `mapping_rules`.

## 2. Required Identifiers

```yaml
schema_id: announcement_doc
template_id: announcement_doc_base_v1
version: 1.0.0
```

`schema_id` must match `target_schema.schema_id`. `template_id` must match the metadata template and package template identifier.

## 3. Field Aliases

Aliases connect UIR candidate names to target field ids.

```yaml
aliases:
  title:
    - title
    - event title
    - document_title
```

Every required target field should have at least one alias or regex rule.

## 4. Regex Rules

Regex rules extract values from source text when candidate labels are not enough.

```yaml
regex_rules:
  - target_field_id: event_time
    pattern: "event time\\s*[:：]\\s*(\\d{4}-\\d{1,2}-\\d{1,2}\\s+\\d{1,2}:\\d{2})"
    group: 1
```

## 5. Transform Rules

Transform rules normalize mapped values after alignment.

```yaml
transform_rules:
  - rule_id: normalize_event_time
    operation: normalize_datetime
    target_field_id: event_time
```

## 6. Defaults

Defaults provide values when a field is intentionally optional or safe to synthesize.

```yaml
defaults:
  location: ""
```

## 7. Enum Maps

Enum maps normalize source labels to target enum values.

```yaml
enum_maps:
  status:
    open: active
```

## 8. Negative Pairs

Negative pairs block confusing source-target matches.

```yaml
negative_pairs:
  - source_pattern: "publish date|retrieved_at"
    target_field_id: event_time
    reason: "publish or retrieved time is not event time"
    severity: block
```

## 9. Thresholds

Thresholds define mapping confidence behavior for the schema pack.

```yaml
thresholds:
  auto_accept: 0.82
  review_required: 0.62
```

## 10. Candidate Hints

Candidate hints are explicit extraction hints supplied by configuration.

```yaml
candidate_hints:
  labeled_values:
    organizer:
      - organizer
    event_time:
      - event time
```

In the inline API, candidate hints are passed through `options.candidate_profile` until the internal model accepts the full external contract directly.

## 11. Internal Model Compatibility

The current `MappingTemplate` model accepts `aliases`, `regex_rules`, `transform_rules`, `defaults`, and `enum_maps`. External `mapping_rules.yaml` may also document `negative_pairs`, `thresholds`, and `candidate_hints`; inline conversion passes those through `options` today.

## 12. Examples

See:

```text
schema_packs/examples/announcement_doc/mapping_rules.yaml
schema_packs/examples/event_notice_doc/mapping_rules.yaml
examples/topic5_inline/announcement_convert_request.json
examples/topic5_inline/event_notice_convert_request.json
```

## 13. SchemaPack Phase 3 Relationship

`mapping_rules.yaml` is one manifest-referenced asset in the versioned SchemaPack contract. It remains responsible for candidate-to-target alignment, transformations, negative pairs, thresholds, and candidate hints. `output_assertions.yaml` is a separate deterministic safeguard over final converted output.

When the same badcase appears in both layers, the checks are complementary: the mapping layer prevents or reviews an incorrect source-target assignment, while the conversion assertion layer detects an invalid final relationship. Assertion definitions must not be tuned into mapping implementation code.
