# SchemaPack Configuration

SchemaPack assets are external configuration inputs for the Topic 5 conversion agent. They are not hard-coded system capability boundaries.

Each SchemaPack should contain:

- `target_schema.json`: target output schema.
- `metadata_template.json`: document-level metadata template.
- `mapping_rules.yaml`: public mapping rules configuration.
- `content_org.yaml`: chunking, tags, summaries, keywords, and source-link policy.
- `router_rules.yaml`: optional recommendation rules for choosing a SchemaPack from UIR evidence.

The primary Topic 5 inline input model is:

```text
UIR + Target Schema + Metadata Template + Mapping Rules + Content Organization Config
```

The current examples include:

- `announcement_doc`
- `event_notice_doc`

Historical packs such as policy, meeting, procurement, contract, or general document configurations are examples and benchmarks only. A new target structure should normally be onboarded by adding a SchemaPack, not by changing core backend code.

Useful references:

- `docs/topic5_convert_api.md`
- `docs/mapping_rules_contract.md`
- `docs/schema_pack_onboarding_checklist.md`

Validation:

```powershell
python scripts/validate_schema_pack.py schema_packs/examples/announcement_doc
python scripts/validate_schema_pack.py schema_packs/examples/event_notice_doc
```

## Versioned Phase 3 Contract

Each migrated SchemaPack uses `schema_pack.yaml` as the canonical manifest. Runtime services load asset paths from `assets`; they do not guess filenames. `output_assertions.yaml` is optional and defines deterministic conversion output assertions.

The runtime model and generated schemas are:

- `backend/app/schemas/schema_pack_contract.py` and `schema_pack_contract.schema.json`;
- `backend/app/schemas/conversion_assertions.py` and `output_assertions_contract.schema.json`.

Positive examples and badcases are executable regression assets. Run:

```powershell
python scripts/eval_schema_pack_contracts.py --all-examples --verify-package --out reports/schema_pack_contract_all.json --markdown reports/schema_pack_contract_all.md
python scripts/check_schema_pack_contract_gate.py --fail-on-gate
```

Output assertions are optional. Existing Package 1.1 deliverables and legacy Topic 5 requests remain supported.
