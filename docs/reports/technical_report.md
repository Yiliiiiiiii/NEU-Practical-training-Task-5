# Technical Report

SchemaPack Agent implements:

```text
UIR -> Schema -> Mapping -> Transform -> Canonical -> Render -> Validate -> Manifest -> Zip -> External Verify
```

Phase 10 adds:

- External package verifier module and CLI.
- Auditable LLM fallback with disabled, mock, and OpenAI-compatible modes.
- Deterministic task replay with `parent_task_id`.
- Expanded `config_snapshot.json` with mapping lineage and model audit.
- Frozen evaluation fixture with 30 cases and 150 gold mappings.
- Deterministic content labels, chunk labels, upstream entities, and consumer smoke CLI.
- Frozen OpenAPI and delivery docs.

Current automated evaluation fixture result:

```text
Precision 1.0000
Recall    1.0000
F1        1.0000
```

This is a project-owned synthetic regression fixture. Human spot-check of gold mappings is still required before using these numbers as external accuracy claims.
