# SchemaPack Package Spec

SchemaPack packages are deterministic ZIP bundles for downstream consumers.

## Required Files

Every `standard_package.zip` must contain:

- `content.json`: structured canonical output for machines.
- `content.md`: human-readable Markdown rendering.
- `chunks.jsonl`: one JSON object per retrieval/training chunk.
- `mapping_report.json`: mapping decisions, evidence, confidence, and risks.
- `transform_report.json`: transform summary, warnings, and errors.
- `validation_report.json`: schema and artifact validation result.
- `content_organization_report.json`: chunk strategy and quality summary.
- `canonical.json`: canonical model snapshot.
- `metadata.json`: package-level schema/template/task metadata.
- `manifest.json`: file roles, media types, byte sizes, and SHA-256 checksums.
- `verifier_report.json`: verifier output generated before ZIP creation.

## Manifest

`manifest.json` uses `manifest_version` `1.1`. Each file entry includes:

- `path`
- `required`
- `media_type`
- `sha256`
- `bytes`
- `role`

Strict verification requires required files to exist, manifest checksums and byte
sizes to match, roles/media types to match the package spec, JSON files to parse,
`chunks.jsonl` to be valid JSONL, and Markdown to be non-empty.

## Metadata

`metadata.json` records package, task, schema, and template identifiers plus an
`artifact_roles` map. Consumers should prefer `metadata.json` for schema and
template ids, and fall back to `manifest.generator` for older packages.

## Chunks

Chunk rows are backward-compatible JSON objects. New rows may include:

- `strategy`
- `granularity`
- `parent_chunk_id`
- `title_path`
- `token_estimate`
- `char_count`
- `source_block_ids`
- `source_links`
- `content_tags`
- `management_tags`
- `quality_tags`
- `quality_flags`
- `summary`
- `keywords`

Downstream scripts accept `--granularity child|parent|all` for parent-child
packages.
