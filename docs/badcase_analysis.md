# Badcase Analysis

SchemaPack Agent keeps badcase checks as regression gates so new mapping,
knowledge, or LLM-adjacent features do not silently degrade output quality.

## Badcase Types

| Type | Risk | Protection |
| --- | --- | --- |
| Confusing source alias | A source field resembles the wrong target field. | Mapping confidence and badcase filters keep it review-required. |
| Over-eager fuzzy match | Similar labels map to the wrong schema field. | Low-confidence fuzzy matches enter review instead of auto-acceptance. |
| Unsafe knowledge activation | A reviewed alias could violate known forbidden mappings. | Badcase hits are blocked before active-pack effect. |
| LLM overreach | Model suggestions could appear plausible but wrong. | LLM fallback is disabled by default, adapter-driven, capped per task, and always review-required. |
| LLM provider outage | Timeout or network failure could stop deterministic conversion. | Non-strict mode records a mapping warning and review item; only explicit `strict_llm=true` fails the task. |
| LLM secret leakage | Credentials could enter task options, snapshots, reports, or audit metadata. | Credentials are environment-only; secret-looking persisted values are recursively redacted and snapshots keep only non-sensitive configuration. |
| Archived catalog use | Old schema/template versions could be used for new tasks. | Archived versions are rejected for new executions. |
| Snapshot drift | New knowledge packs could mutate historical results. | Task execution snapshots preserve schema/template/effective-template context. |

Mapping reports now expose `risk_flags`, `confidence_tier`,
`review_required_reason`, structured `evidence`, and `badcase_filter` per
mapping decision. Known forbidden source/target pairs receive
`badcase_blocked` and are not accepted automatically.

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

## Non-procurement Recall Badcases

The expanded real-world mapping gold embeds badcases and the standalone
`examples/real_world/gold/real_world_badcases.jsonl` file is kept synchronized
with those embedded `known_badcases` entries. The non-procurement recall work
adds regression coverage for high-risk source/target pairs that must not be
auto-accepted:

| Source label | Forbidden target | Reason |
| --- | --- | --- |
| `发布日期` | `effective_date` | Publication metadata is not automatically the effective date. |
| `主持人` | `attendees` | Meeting host/chair is not the full attendee list. |
| `联系人` | `attendees` | Contact person is not a meeting attendee list. |
| `承办单位` | `issuer` | Organizer/undertaker is not necessarily the issuing authority. |
| `预算金额` | `award_amount` | Budget is not an awarded amount. |
| `控制价` | `award_amount` | Control price is not an awarded amount. |

These badcases protect the recall work from metric gaming: ambiguous or
high-risk evidence should remain review-required unless there is a source-backed
safe rule. The latest package-based non-procurement analysis and API-backed
non-procurement evaluator both record zero badcase violations. The phase gate
still remains open because recall and review-required targets are not yet met.

## Remaining Limitations

- The regression dataset is synthetic and should be expanded with real
  enterprise UIR cases before production rollout.
- Badcase filters are deterministic and rule-based; they do not replace human
  review for ambiguous mappings.
- LLM fallback remains optional and human-gated; provider/model evaluation and
  enterprise monitoring remain deployment responsibilities.
