# Artifact consistency evidence

The deterministic Markdown envelope carries document, summary, embedded structured-data,
and per-block markers. Each canonical block appears exactly once and carries a SHA-256
hash derived from its exact canonical text. Protocol-like source text, table delimiters,
and code fences are escaped without changing canonical source data.

`ArtifactConsistencyService` checks canonical fields and document metadata against JSON,
embedded JSON and extractive summary against Markdown, block identity/order/hash/rendered
content, chunk sources/text/parents/indices, and upstream entity relevance. Its strict report
is returned by inline conversion and persisted by registered execution.

New packages declare `artifact_consistency_v1`, contain a manifested
`artifact_consistency_report.json`, and include `verifier_report.json` in the final manifest.
The package verifier rejects missing, malformed, unmanifested, checksum-mismatched, or
failed consistency reports. Packages that do not declare the feature remain readable.
