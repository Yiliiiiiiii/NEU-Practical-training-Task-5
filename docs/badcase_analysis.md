# Badcase Analysis

SchemaPack Agent keeps badcase checks as regression gates so new mapping,
knowledge, or LLM-adjacent features do not silently degrade output quality.

## Badcase Types

| Type | Risk | Protection |
| --- | --- | --- |
| Confusing source alias | A source field resembles the wrong target field. | Mapping confidence and badcase filters keep it review-required. |
| Over-eager fuzzy match | Similar labels map to the wrong schema field. | Low-confidence fuzzy matches enter review instead of auto-acceptance. |
| Unsafe knowledge activation | A reviewed alias could violate known forbidden mappings. | Badcase hits are blocked before active-pack effect. |
| LLM overreach | Model suggestions could appear plausible but wrong. | LLM fallback is disabled by default, adapter-driven, and always review-required. |
| Archived catalog use | Old schema/template versions could be used for new tasks. | Archived versions are rejected for new executions. |
| Snapshot drift | New knowledge packs could mutate historical results. | Task execution snapshots preserve schema/template/effective-template context. |

## Current Regression Checks

Run:

```powershell
.\backend\.venv\Scripts\python.exe scripts\eval_production_like.py
```

Expected:

```text
production-like eval complete: 15 cases, gold=1.0, badcase=1.0
```

The generated report includes:

- `phase_b.badcase_violation_count`
- `phase_b.badcase_pass_rate`
- per-case `badcases`
- `old_run_snapshot_unchanged`
- `package_validation`
- `downstream_smoke_summary`

## Current Result

The current expected result is:

```text
badcase_violation_count = 0
badcase_pass_rate = 1.0
```

## Remaining Limitations

- The regression dataset is synthetic and should be expanded with real
  enterprise UIR cases before production rollout.
- Badcase filters are deterministic and rule-based; they do not replace human
  review for ambiguous mappings.
- LLM fallback remains optional and must stay human-gated when enabled.
