# SchemaPack Package 规范

SchemaPack packages 是面向下游 consumers 的确定性 ZIP bundles。它们在 mapping、transformation、canonical model construction、rendering、content organization、validation、manifest generation 和 strict package verification 之后生成。

## 必需 Package Artifacts

每个 `standard_package.zip` 必须包含：

- `content.json`：面向机器的 structured canonical output。
- `content.md`：面向人的 Markdown rendering。
- `chunks.jsonl`：每个 retrieval/training chunk 一行 JSON object。
- `mapping_report.json`：mapping decisions、evidence、confidence、risk flags、review-required reasons 和 badcase-filter results。
- `transform_report.json`：transform summary、warnings、errors、normalization、defaults 和 projection details。
- `validation_report.json`：schema 与 artifact validation result。
- `content_organization_report.json`：chunk strategy、summary、quality 和 source-link organization evidence。
- `canonical.json`：带 task、schema/template 和 source references 的 canonical model snapshot。
- `metadata.json`：package-level schema/template/task metadata 与 artifact role map。
- `manifest.json`：required-file registry，包含 roles、media types、byte sizes 和 SHA-256 checksums。
- `verifier_report.json`：ZIP 创建前生成的 verifier output。

## Metadata 与 Snapshot References

`metadata.json` 标识 package、task、document、schema、template、schema version、template version、execution profile 和 artifact roles。Task execution 会在 conversion 前捕获不可变 schema/template snapshots，因此即使 catalog versions 后续变化，package 仍可追溯到执行时使用的治理定义。

Consumers 应使用 `metadata.json` 与 `canonical.json` 获取 schema/template context。旧 packages 可能依赖 `manifest.generator`；当前 packages 应优先使用显式 metadata fields。

## Manifest 哈希

`manifest.json` 使用 `manifest_version` `1.1`。每个 entry 包含：

- `path`
- `required`
- `media_type`
- `sha256`
- `bytes`
- `role`

Verifier 会把每个 manifest entry 与 package 中实际 file bytes 比对。Hash 或 byte-size 不匹配会导致 verification 失败。

## 带来源链接的 Chunks

`chunks.jsonl` 行是向后兼容的 JSON objects。当前行可能包含：

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

Source links 与 source block IDs 是 traceability aids。它们让 downstream retrieval 或 training-corpus consumers 可以把 chunk 追溯到生成它的 UIR blocks。

## Hard-Gap Batch 1 Feature Artifacts

Package 1.1 remains feature-aware and backward compatible. New conversion packages may
declare these values in `metadata.json.features`:

- `metadata_template_v1` requires a valid, manifested `metadata_template_report.json`.
- `document_summary_v1` records one shared extractive summary.
- `artifact_consistency_v1` requires a valid, manifested, passing
  `artifact_consistency_report.json`.

The final manifest includes `verifier_report.json` with role `verifier_report`. Package
creation writes semantic artifacts, performs initial verification, writes the verifier
report, rebuilds the final manifest, and verifies the final file set. The manifest never
hashes itself.

Legacy packages that do not declare a new feature retain existing required-file behavior.
Declaring a feature and omitting, corrupting, unmanifesting, or failing its report is a
verifier error. Verification remains structural and cross-artifact; it is not a Topic 6
quality score, grade, or semantic-fidelity judgment.

`content.md` contains machine-readable `topic5:*` comment envelopes. Each canonical block
appears exactly once with a SHA-256 text hash. Consumers may ignore HTML comments for
presentation, but must preserve them when using Markdown for consistency checks.

## Consumer Contracts

`contracts/` contains versioned Package 1.1, RAG corpus, training corpus, and
structured CSV contracts. `scripts/verify_consumer_contract.py` validates one
ZIP or a package tree and writes JSON/Markdown evidence. These contracts are
offline consumption profiles; they do not add a vector database, model-training
runtime, or webhook service.

Downstream scripts 对 parent-child packages 支持 `--granularity child|parent|all`：

```powershell
backend\.venv\Scripts\python.exe scripts\smoke_rag_ingest.py --package standard_package.zip --query "procurement supplier amount"
backend\.venv\Scripts\python.exe scripts\export_training_corpus.py --package standard_package.zip --out reports\training_corpus.jsonl --granularity all
```

## Validation 与 Content-Organization Reports

`validation_report.json` 记录 schema-level 与 artifact-level validation。对于 real-world data，package 可以通过 verifier checks，同时 field-level semantic validation 仍保持 review-required。这种区分是有意设计，下游说明中不能把两者混为一谈。

`content_organization_report.json` 记录 chunking strategy、protected block handling、summaries、tags、quality flags 和 aggregate chunk metrics。32-query retrieval evaluator 使用这些 chunks 衡量确定性 retrieval evidence，例如 `Recall@3`。

## Strict Verifier 检查

Strict package verification 检查：

- 所有 required files 存在；
- manifest entries 与实际 file paths 匹配；
- SHA-256 hashes 与 byte sizes 匹配；
- 声明的 media types 与 roles 符合 package spec；
- JSON files 可成功解析；
- `chunks.jsonl` 是合法 JSONL，并包含 required chunk fields；
- Markdown content 非空；
- verifier output 已包含在 package 中。

Package verification 证明 structural integrity、checksum consistency、artifact presence、parseability 和 traceability。它不代表每个 target field 都通过 strict semantic validation；该区别应查看 `validation_report.json` 和 evaluation reports。

## Lineage Task Reports（MVP）

`lineage_graph.json` 与 `lineage_summary.json` 当前是 task reports，不是
Package 1.1 ZIP artifacts。Lineage graph 仍会读取最终 manifest entries，记录
现有 package artifacts 的 path、role、media type、bytes 与 SHA-256，并连接到
consumer contract。

暂不把 lineage 自身加入 ZIP，是为了避免 graph 引用最终 manifest hash 时形成
自引用 checksum，同时保持 required file list、strict verifier 和现有 consumer
contracts 不变。后续若加入 ZIP，必须先定义独立的非自引用 lineage contract，
再同步 ManifestService、PackageVerifierService 与所有 downstream contracts。
