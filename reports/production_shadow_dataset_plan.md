# Production Shadow Dataset Plan

Current status: not enough independent production UIR + gold labels are available in this workspace to honestly claim a production blind-set 0.85 result.

## Proposed structure

```text
examples/production_shadow/
  manifest.json
  warmup/{general,meeting,policy}/
  blind/{general,meeting,policy}/
  gold/mapping_gold.jsonl
  gold/badcases.jsonl
```

## Minimum acceptance before 0.85 claim

- blind-set average_recall >= 0.85
- auto_accepted_precision >= 0.95
- mapped_or_review_recall >= 0.90
- badcase_violations = 0
- llm_auto_accepted_count = 0
- secret_leaks = 0
