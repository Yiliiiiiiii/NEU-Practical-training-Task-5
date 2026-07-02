# Non-procurement Schema Adjustments

| doc_type | field | old_rule | new_rule | reason | affected_docs | risk | reviewer_note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| general_doc | required fields | title, content | unchanged | Existing requirements are already limited to core identity and content fields. | 4 | none | Do not relax for metric gain. |
| meeting_doc | required fields | meeting_title, meeting_date, content | unchanged | These remain the minimum evidence-backed meeting representation. | 6 | missing dates remain visible | Improve extraction before reconsidering schema. |
| policy_doc | required fields | title, issuer, publish_date, content | unchanged | These remain the minimum evidence-backed policy representation. | 10 | missing issuer/date remain visible | Improve extraction and aliases before reconsidering schema. |

No `required` field was removed in this iteration.
