# Topic 5 Tag Quality v2

## Annotation protocol and claim boundary

An independent dataset annotator reads only the source-hashed UIR blocks named in
the annotation specification, assigns content semantics, and records deterministic
management/quality expectations with exact rule, trace, and chunk scope. Semantic
anchor blocks were selected without projecting the earlier correlated gold groups.
Reviewer role is `independent_dataset_annotator`; claims are limited to
`public_fixture_baseline_only`. No production-blind claim is made.

## Tag definitions

Every tag and definition is machine-readable in `taxonomy.json`. Content tags are
independent semantic labels scored with multilabel Jaccard accuracy and separately
reported precision/recall/F1. Management and quality
tags are deterministic contracts scored only for exact rule, trace, and scope.
`schema:*` identifies the configured schema; `template_version:*` identifies its
template version; `source_linked` requires source IDs; `anchor_linked` requires
resolvable canonical anchors.

## Immutability

The manifest hashes every payload and baseline file; an external seal hashes the
manifest itself. Corrections require v3, a reason, and before/after reports.
