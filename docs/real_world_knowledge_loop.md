# Real-world knowledge loop

This evaluation exercises the human-review-to-knowledge-pack path for the
real-world procurement catalog without mutating the production catalog snapshot.

The fixture in
`examples/real_world/review_fixtures/procurement_review_decisions.jsonl` contains
one approved alias and one semantic rejection. The approved alias is activated
through `ReviewKnowledgeWorkflowService`, accepted into a knowledge pack, and
resolved with the existing effective-template service. The rejected candidate is
kept out of activation so an ambiguous control price cannot become a winning
amount.

Run:

```powershell
F:\p2\backend\.venv\Scripts\python.exe scripts\eval_real_world_knowledge_loop.py
```

Outputs:

- `reports/real_world_knowledge_loop_report.json`
- `reports/real_world_knowledge_loop_report.md`

The report includes before/after mapping counts, decision evidence,
badcase-violation count, activated aliases, remaining ambiguous cases, and an
`old_snapshot_unchanged` guard.

## Review Knowledge Growth Evaluator

`scripts/eval_review_knowledge_growth.py` uses an isolated SQLite database and
catalog copy. It runs a fixed real policy UIR before and after review decisions
and active-pack activation. The report proves that approved aliases affect only
future tasks, rejected and badcase aliases do not activate, draft packs have no
effect, and the original metadata/canonical/mapping/execution snapshots remain
unchanged.
