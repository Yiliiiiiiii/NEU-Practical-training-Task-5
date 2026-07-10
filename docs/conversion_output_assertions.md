# Conversion Output Assertions

## Purpose

`output_assertions.yaml` contains versioned, deterministic checks over Topic 5 converted JSON. The runtime source of truth is `backend/app/schemas/conversion_assertions.py`; the generated external schema is `schema_packs/output_assertions_contract.schema.json`.

Conversion output assertions are deterministic SchemaPack-scoped checks over Topic 5 converted output. They complement target-schema validation but do not implement Topic 6 quality scoring, grading, semantic fidelity evaluation, or routing recommendations.

## Contract

Each assertion has a stable unique `assertion_id`, a supported JSON path, an operator, `error` or `warning` severity, optional behavior, operator parameters, and an optional message. Supported paths use only `$`, object fields, and numeric array indexes. Wildcards, filters, recursive descent, and executable expressions are rejected.

Required deterministic operators are `exists`, `non_empty`, `type_is`, `date_format`, `datetime_format`, `regex_match`, `enum_allowed`, `number_range`, `text_length`, `array_length`, `url_like`, `equal_to_path`, and `not_equal_to_path`.

Regex patterns and operator parameters are validated while the SchemaPack contract loads. Assertions never make remote requests and never invoke an LLM.

## Result Semantics

`ConversionAssertionService` emits `ConversionAssertionReport` with deterministic results and issues. `passed` means `error_count == 0`; warnings do not fail the report. A missing optional primary path is skipped. For optional cross-path checks, a missing `other_path` is also skipped because the relationship applies only when both values are present.

Issues include the assertion ID, severity, path, operator, expected value, bounded actual preview, and available mapping evidence. Strings are limited to 200 characters, arrays to five preview items, and objects to a ten-key summary.

Conversion status behavior:

- no errors: conversion can remain `completed`;
- warning-only failures: conversion can remain `completed`;
- assertion errors: `review_required` by default;
- assertion errors with `strict_output_assertions=true`: `failed`.

This status only describes compliance with the declared Topic 5 conversion contract.

## Request And Manifest Precedence

```text
request option
> manifest execution default
> application default
```

Inline requests may provide `output_assertions`. Registered tasks may provide `schema_pack_id`; the runtime then loads manifest assets and assertions. `include_assertion_report_in_package` controls optional Package 1.1 inclusion.

## Evidence

Registered task execution writes `tasks/<task_id>/conversion_assertion_report.json` atomically. The execution snapshot exposes the same path as `artifacts.conversion_assertion_report`; it is also available through task report paths and `/api/v1/tasks/<task_id>/reports/assertions`.

## Non-goals

- no quality score;
- no quality grade;
- no publication route;
- no semantic fidelity judgment;
- no LLM-as-Judge;
- no Topic 11 retrieval optimization.
