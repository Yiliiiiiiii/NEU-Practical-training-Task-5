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
