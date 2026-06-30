# SchemaPack Package Spec

SchemaPack packages are deterministic ZIP bundles for downstream consumers.
They are produced after mapping, transformation, canonical model construction,
rendering, content organization, validation, manifest generation, and strict
package verification.

## Required Package Artifacts

Every `standard_package.zip` must contain:

- `content.json`: structured canonical output for machines.
- `content.md`: human-readable Markdown rendering.
- `chunks.jsonl`: one JSON object per retrieval/training chunk.
- `mapping_report.json`: mapping decisions, evidence, confidence, risk flags,
  review-required reasons, and badcase-filter results.
- `transform_report.json`: transform summary, warnings, errors, normalization,
  defaults, and projection details.
- `validation_report.json`: schema and artifact validation result.
- `content_organization_report.json`: chunk strategy, summary, quality, and
  source-link organization evidence.
- `canonical.json`: canonical model snapshot with task, schema/template, and
  source references.
- `metadata.json`: package-level schema/template/task metadata and artifact role
  map.
- `manifest.json`: required-file registry with roles, media types, byte sizes,
  and SHA-256 checksums.
- `verifier_report.json`: verifier output generated before ZIP creation.

## Metadata And Snapshot References

`metadata.json` identifies the package, task, document, schema, template,
schema version, template version, execution profile, and artifact roles. Task
execution captures immutable schema/template snapshots before conversion so a
package can be traced back to the governed definitions used at execution time,
even after catalog versions change.

Consumers should use `metadata.json` and `canonical.json` for schema/template
context. Older packages may rely on `manifest.generator`; current packages
should prefer explicit metadata fields.

## Manifest Hashes

`manifest.json` uses `manifest_version` `1.1`. Each entry includes:

- `path`
- `required`
- `media_type`
- `sha256`
- `bytes`
- `role`

Verifier checks compare each manifest entry with the actual file bytes in the
package. Hash or byte-size mismatch fails verification.

## Source-Linked Chunks

`chunks.jsonl` rows are backward-compatible JSON objects. Current rows may
include:

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

Source links and source block IDs are traceability aids. They allow downstream
retrieval or training-corpus consumers to connect a chunk back to the UIR blocks
that produced it.

Downstream scripts accept `--granularity child|parent|all` for parent-child
packages:

```powershell
backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package standard_package.zip --query "procurement supplier amount"
backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package standard_package.zip --out reports\training_corpus.jsonl --granularity all
```

## Validation And Content-Organization Reports

`validation_report.json` records schema-level and artifact-level validation.
For real-world data, a package can pass verifier checks while field-level
semantic validation remains review-required. That split is intentional and must
not be collapsed in downstream claims.

`content_organization_report.json` records the chunking strategy, protected
block handling, summaries, tags, quality flags, and aggregate chunk metrics.
The 32-query retrieval evaluator uses these chunks to measure deterministic
retrieval evidence such as `Recall@3`.

## Strict Verifier Checks

Strict package verification checks:

- all required files exist;
- manifest entries match actual file paths;
- SHA-256 hashes and byte sizes match;
- declared media types and roles match the package spec;
- JSON files parse successfully;
- `chunks.jsonl` is valid JSONL and contains required chunk fields;
- Markdown content is non-empty;
- verifier output is included in the package.

Package verification proves structural integrity, checksum consistency,
artifact presence, parseability, and traceability. It does not imply every
target field passed strict semantic validation; consult `validation_report.json`
and the evaluation reports for that distinction.
