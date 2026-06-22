# Phase 5 Implementation Plan: Transform Engine & Canonical Model

## Overview

Phase 5 implements field transformation and canonical model construction, enabling the pipeline to convert mapped fields into a unified canonical model.

## Tasks

### 5.1-5.5 Transform Engine Operations

**File**: `backend/app/engines/transform_engine.py`

Implemented operations:
- **rename**: Source value written to target field
- **type_cast**: string/int/float/bool/date conversions
- **date_format**: Chinese date strings (`2026年6月1日`) to ISO `YYYY-MM-DD`
- **enum_map**: Enum value mapping with warning on miss
- **default**: Default value fill for missing fields
- **merge**: Combine multiple source fields into one target
- **split**: Split one source field into multiple targets

### 5.6 Trace Service

**File**: `backend/app/services/trace_service.py`

- Records each transform action to `transform_traces` table
- Supports batch recording from engine trace events
- Exports `trace.json` via `export_trace_json()`
- All events include: stage, action, target_field_id, before/after values, rule_id, reason, status

### 5.7 Canonical Builder & Service

**Files**:
- `backend/app/engines/canonical_builder.py`
- `backend/app/services/conical_service.py`

CanonicalBuilder:
- Constructs `CanonicalModel` from UIR blocks, assets, metadata, and transformed fields
- Preserves block_id, source_blocks, text_hash for each block
- Preserves asset references

CanonicalService:
- Orchestrates transform execution and canonical model construction
- Loads confirmed mappings, executes transform engine, builds canonical model
- Persists to `canonical_models` table and `tasks/{task_id}/canonical_model.json`
- Records transform traces via TraceService
- Updates task status to `rendered`

## Files Created/Modified

| File | Action |
|------|--------|
| `backend/app/engines/transform_engine.py` | Created |
| `backend/app/services/trace_service.py` | Created |
| `backend/app/engines/canonical_builder.py` | Created |
| `backend/app/services/canonical_service.py` | Created |
| `backend/tests/test_transform_engine.py` | Created (15 tests) |
| `backend/tests/test_trace_service.py` | Created (5 tests) |
| `backend/tests/test_canonical_builder.py` | Created (4 tests) |

## Test Results

- Total: 67 passed (43 baseline + 24 new)
- Ruff: All checks passed
- New test coverage: transform engine (15), trace service (5), canonical builder (4)
