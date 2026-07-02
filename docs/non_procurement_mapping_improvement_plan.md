# Non-procurement Mapping Improvement Plan

## Baseline

Average recall 0.3494; review-required 145; required missing 18; strict pass 4/20; badcase violations 0.

## Current Analyzer Snapshot

Average recall 0.4211; review-required 139; required missing 15; strict pass 4/20; badcase violations 0.

## High-frequency Fix Items

| ID | doc_type | target_field | count | gap_type | action | files_to_change | risk | expected_gain |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| F01 | meeting_doc | topics | 5 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 5 topics gap(s) |
| F02 | general_doc | application_conditions | 4 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 4 application_conditions gap(s) |
| F03 | policy_doc | issuer | 4 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 4 issuer gap(s) |
| F04 | general_doc | service_object | 3 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 3 service_object gap(s) |
| F05 | meeting_doc | meeting_date | 3 | regex_missing | add_regex | examples/production_like/mapping_templates/*.json; backend/tests/test_non_procurement_templates.py | high | reduce 3 meeting_date gap(s) |
| F06 | policy_doc | publish_date | 3 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 3 publish_date gap(s) |
| F07 | meeting_doc | meeting_date | 2 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 2 meeting_date gap(s) |
| F08 | general_doc | service_object | 1 | regex_missing | add_regex | examples/production_like/mapping_templates/*.json; backend/tests/test_non_procurement_templates.py | high | reduce 1 service_object gap(s) |
| F09 | meeting_doc | meeting_number | 1 | candidate_not_extracted | enhance_candidate | backend/app/services/candidate_service.py; backend/tests/test_candidate_service_non_procurement.py | medium | reduce 1 meeting_number gap(s) |

## Candidate Extraction Fixes

- `meeting_doc.topics` (5): candidate_not_extracted / enhance_candidate from agenda sections, first agenda item, reviewed matters, 习近平主席.
- `general_doc.application_conditions` (4): candidate_not_extracted / enhance_candidate from process or condition detail, 申请专项资金支持的单位.
- `policy_doc.issuer` (4): candidate_not_extracted / enhance_candidate from issuer or issuing body, issuing bodies, 发文机构, 国务院办公厅.
- `general_doc.service_object` (3): candidate_not_extracted / enhance_candidate from service or subject section.
- `policy_doc.publish_date` (3): candidate_not_extracted / enhance_candidate from 2025-01-16, publication date or date sentence, signed date.
- `meeting_doc.meeting_date` (2): candidate_not_extracted / enhance_candidate from meeting date sentence, 二〇二五年十一月三日.
- `meeting_doc.meeting_number` (1): candidate_not_extracted / enhance_candidate from 汨政办发〔2026〕8号.

## Template Alias Fixes

- No safe automatic item selected from the current ranked recommendations.

## Regex Rule Fixes

- `meeting_doc.meeting_date` (3): regex_missing / add_regex from 2026-06-16, meeting sentence, opening sentence.
- `general_doc.service_object` (1): regex_missing / add_regex from 申报对象.

## Schema Adjustments

- No safe automatic item selected from the current ranked recommendations.

## Transform Fixes

- No safe automatic item selected from the current ranked recommendations.

## Badcase Additions

- No safe automatic item selected from the current ranked recommendations.

## Rejected Automatic Rules

- `policy_doc.source` (10, alias_missing): rejected because source_block_ids is empty, source label is generic metadata.
- `meeting_doc.source` (6, alias_missing): rejected because source_block_ids is empty, source label is generic metadata.
- `general_doc.source` (4, alias_missing): rejected because source_block_ids is empty, source label is generic metadata.

## Verification Commands

```powershell
backend\.venv\Scripts\python.exe scripts\analyze_non_procurement_gaps.py --packages-root reports\real_world_packages --gold examples\real_world\gold\mapping_gold.jsonl --badcases examples\real_world\gold\real_world_badcases.jsonl --out reports\non_procurement_gap_analysis.json --markdown reports\non_procurement_gap_analysis.md
backend\.venv\Scripts\python.exe scripts\eval_non_procurement_mapping.py --base-url http://127.0.0.1:8000 --timeout 60 --baseline reports\non_procurement_baseline_report.json --out reports\non_procurement_mapping_eval_report.json --markdown reports\non_procurement_mapping_eval_report.md
```
