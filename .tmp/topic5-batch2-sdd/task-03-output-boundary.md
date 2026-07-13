# Task 3: Business Output Metadata Boundary

Create the explicit business-facing `content.json` shape:

```json
{
  "source_metadata": {},
  "document_metadata": {},
  "metadata_template": {},
  "document_summary": {},
  "data": {},
  "blocks": [],
  "assets": []
}
```

Internal execution snapshots, mapping/transform summaries, metadata reports, traces, report paths, runtime duration, task/package IDs, secrets, and other operational state must not appear anywhere in business output. Operational data remains in dedicated artifacts/reports. Keep a deprecated legacy `metadata` field only if existing consumer tests prove it is required; if kept, it must contain only safe source/document metadata and have documented deprecation. Add recursive forbidden-key scanning tests for inline output and packaged `content.json`, plus compatibility tests for any retained field. Update renderer/canonical boundaries minimally; do not perform summary migration, transform changes, package redesign, or engine extraction in this task.

Use TDD (RED then GREEN), run affected render/inline/package/entity/summary tests and Ruff. Report to `.tmp/topic5-batch2-sdd/task-03-report.md`; scoped commit `fix: separate business metadata from operational reports`; never stage `.tmp` or user files.
