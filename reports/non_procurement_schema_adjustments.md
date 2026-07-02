# 非采购 Schema 调整记录

| doc_type | field | old_rule | new_rule | reason | affected_docs | risk | reviewer_note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| general_doc | required fields | title, content | unchanged | 现有 required fields 已限制在核心 identity 与 content。 | 4 | none | 不为提升指标而放松。 |
| meeting_doc | required fields | meeting_title, meeting_date, content | unchanged | 这些字段仍是 evidence-backed meeting representation 的最低要求。 | 6 | missing dates remain visible | 先改进 extraction，再重新评估 schema。 |
| policy_doc | required fields | title, issuer, publish_date, content | unchanged | 这些字段仍是 evidence-backed policy representation 的最低要求。 | 10 | missing issuer/date remain visible | 先改进 extraction 与 aliases，再重新评估 schema。 |

本轮没有删除任何 `required` field。
