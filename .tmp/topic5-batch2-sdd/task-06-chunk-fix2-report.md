# Task 6 chunk coverage second review fix

## Root causes fixed

- Artifact consistency treated table/list/code blocks as unconditionally protected, while Topic 11 honored the configured `protect_*` flags. The flags now propagate through inline, registered, package-build, and disk-reverification paths.
- Duplicate grouping used chunk IDs as graph nodes and whole connected components, which collapsed duplicate IDs and sibling duplicates. Metrics now use record comparisons, reject duplicate IDs independently, and exempt only actual ancestor/descendant pairs.
- Non-empty text with only unknown sources skipped the unexplained-text metric. It now increments both unknown-source and unexplained-text evidence.

## TDD and verification

- Inherited RED regressions covered disabled table protection, duplicate IDs, sibling duplicates, and unknown-only text.
- Focused artifact consistency, Topic 11, and chunk organizer suite: 73 passed.
- Focused Ruff: passed.

Production chunk content and task/chunk identity semantics are unchanged.
