# Handoff Status

Last updated: 2026-06-25

## Current Status

The project is in a usable handoff state.
Core UIR-to-schema workflow is in place, and the mapping knowledge growth loop now supports controlled, human-gated expansion from real runs.

## Completed Work

- UIR import, task creation, candidate generation, mapping, review, conversion, rendering, validation, packaging, and ZIP download
- Deterministic mapping with exact, alias, regex, type, and fuzzy strategies
- LLM fallback after deterministic mapping
- Mapping report generation and package verifier evidence
- Real-run capture, learning candidate derivation, candidate review, knowledge pack creation, pack activation, and knowledge metrics
- Effective template resolution from active knowledge packs before deterministic mapping
- Frontend knowledge review page for candidate approval, pack creation, pack activation, and metrics

## Key Principles

- Deterministic mapping stays first
- LLM fallback only runs after deterministic mapping
- Knowledge growth is explicit and human approved
- Only active packs affect runtime mapping
- Draft or pending packs do not change runtime behavior

## Knowledge Growth Flow

1. Capture a real run from a completed task.
2. Derive learning candidates from reviewed mappings, transform errors, and unmapped required fields.
3. Review candidates and approve or reject them.
4. Create draft knowledge packs from approved candidates.
5. Explicitly activate packs.
6. Resolve active packs into effective mapping templates.
7. Run deterministic mapping with the resolved template.

## Key Files and Entry Points

Backend:

- `backend/app/api/v1/knowledge.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/effective_template_service.py`
- `backend/app/services/mapping_service.py`

Frontend:

- `frontend/src/pages/KnowledgePage.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`

Docs:

- `README.md`
- `docs/openapi.json`

## Verification Status

Recent validation completed successfully:

- Backend full test suite: passed
- Frontend full test suite: passed
- Backend focused knowledge/effective-template/API-contract/fallback suite: passed
- Frontend targeted knowledge/workflow shell tests: passed
- Frontend lint: passed
- Frontend production build: passed

## Risks and Boundaries

- The growth loop only learns mapping knowledge and evaluation assets.
- It does not train models.
- It does not parse raw documents, OCR outputs, PDF, Word, Excel, or images.
- It does not clean or normalize source data.
- It does not bypass human approval.
- Runtime behavior depends on active packs only.
- Older mojibake UI labels still exist elsewhere in the repository and were left untouched.

## Next Steps

- Continue collecting real UIR, Schema, and mapping-rule variants from production-like usage.
- Keep validating that effective templates resolve correctly before deterministic mapping.
- Expand review and activation workflows only if new operational cases require them.
- Keep `docs/openapi.json` and `README.md` aligned with the current behavior.
