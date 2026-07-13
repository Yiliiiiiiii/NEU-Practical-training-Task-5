# Task 4 semantic hash follow-up

- Root cause: the golden semantic-hash helper removed the `task_id` field but still hashed task-derived `chunk_id`, `parent_chunk_id`, and document-summary `source_chunk_ids`. Task 4 correctly made those runtime identities use the real generated task ID, so identical semantic runs acquired different raw identity strings.
- Fix: normalize only the current run's task-ID namespace to a placeholder inside the test comparison layer. Production chunks and summary references remain unchanged.
- Added referential-integrity assertions proving every summary `source_chunk_id` points to an emitted chunk before normalization.
- Verification: 4 golden-package tests passed; focused Ruff passed.
