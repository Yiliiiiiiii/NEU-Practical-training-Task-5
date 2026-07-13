# Task 4: Summary Contract Migration and Correct Task IDs

- Make `summary.chunk_mode` and `summary.document_mode` the only source of truth.
- Accept legacy top-level `summary_mode` for one release. If nested `summary.chunk_mode` was not explicitly supplied, migrate the old value. If old and new are both supplied and differ, reject validation. Emit a deterministic deprecation warning into `ContentOrganizationReport` whenever old input is used.
- Update bundled SchemaPack content organization configs to the new nested form and remove contradictory duplicate settings.
- Ensure internal chunk construction receives the real task ID; never pass doc ID as task ID or derive chunk IDs from it accidentally. Preserve document ID separately.
- Add contract migration, conflict, warning, SchemaPack validation, and chunk-ID tests.

Use TDD; do not change transform heuristics, package finalization, or full engine. Run affected content organization, Topic11, SchemaPack contract, inline/registered tests and Ruff. Report to `.tmp/topic5-batch2-sdd/task-04-report.md`; scoped commit `refactor: consolidate content organization contract`; never stage `.tmp` or user files.
