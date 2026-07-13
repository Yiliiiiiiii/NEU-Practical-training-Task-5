# Task 7 Report: Frozen v2 Benchmarks

## Scope and production boundary

- Dataset/evaluator/baseline only. No production mapping or tag implementation changed.
- Final independent freeze commits: `fd178577` (tag) and `4a1abbe5` (mapping).
- The correction history was rewritten before Task 8, so the immutable boundary contains exactly these two clean commits after engine commit `70ff3023`.

## Tag quality v2 corrected freeze

- Independent annotation source: `eval/topic5_tag_quality/v2_annotation_spec.jsonl`; the frozen byte-identical copy is `v2/annotation_spec.jsonl` and both are SHA-bound by the root manifest.
- Builder contains no reference to `examples/real_world/gold` or `content_organization_gold`; it reads the explicit annotation spec and source UIR only, refuses overwrite unless `--force`, generates the baseline, and hashes every file except the non-circular root manifest itself.
- All 20 annotations record semantic rationale, reviewer role `independent_dataset_annotator`, and claim boundary `public_fixture_baseline_only`. Semantic anchor selections differ from the earlier correlated block groups.
- Root manifest seal SHA: `b6978c410382b3791336021688414821e328d3d25f6db4457bb1d550e057a4a4`; dataset SHA: `e7ca97df7aaef99333b2d443118de6f7c7194432221b4a6c135e195fa06e0163`; immutable payload SHA: `503321bfc890b60af884111bbffd62b27d5cfb1375a716bba9ceeae7a81f243f`. The baseline engine identity is pinned to pre-freeze engine commit `70ff30236d90a3c9de0534a8f6313e5bb559cbf5`, so builder byte equality remains stable after later dataset-only commits.
- 20 samples. Content semantic precision/recall/F1: 0.7407407407 / 1.0 / 0.8510638298. Unknown runtime tag count is recorded honestly as 7.
- Management and quality rule, exact-trace-set, and exact-scope-set correctness are each 1.0. Extra actual trace/scope records fail correctness.
- Taxonomy/card define every content, management, and quality tag. Validation covers version/counts, duplicate labels/refs, annotation source SHA, internal UIR doc IDs, block refs, tag schemas, trace schemas, frozen drift, unexpected files, and builder byte equality.

## Mapping v2 corrected freeze

- Versioned authored source: `eval/topic5_mapping_v2_source/`. The builder only copies reviewed static schemas, rules, UIR, annotations, negative/no-match decisions, and splits, then freezes hashes. It no longer has a shared `FAMILY_FIELDS` or a loop that generates aliases, UIR, and gold together.
- 90 documents; 6 genuinely distinct families; exactly 15 per family; 534 positive mappings; 180 unique negative/no-match source decisions. Negative-pair and no-match source sets are disjoint.
- Split: 45 dev / 45 test. Schema-held-out count is derived as 15 from actual dev/test schema-set difference. Actual UIR organization/layout holdout rate is 0.6666666667.
- Exact-name positive rate: 0.0. Unicode casefold/alphanumeric normalization plus dangerous substring checks in both directions scan doc IDs, metadata candidate keys, and every nested candidate-bearing attribute. Frozen audit passes with zero violations.
- Variety is derived from actual UIR/schema/gold content (never manifest claims): Chinese/English, abbreviations, long labels, metadata, key-value, table, paragraph, order changes, missing optional fields, multiple date roles, budget/award, issuer/organizer, contact/attendee, and publish/effective date.
- Family-specific source values replace `Recorded value` numeric templates. Meeting contact is a valid contact candidate and only a negative attendee pair; the separate no-match block is unrelated page/logistics noise.
- Dataset SHA: `2e527fb7127e26eb8fbe7f8c579620501624d7922cc8413ed3d424d0d29e8805`.
- Source-contract SHA: `c0a7e3cdb2eb06aedb8f9dd04aadd74475108d65a8fd79897f6c32bbc32d9925`; external root seal SHA: `165f0f36e3e9cd7353fecddf13fdb8d90d2633730938299851e0cfa2f3988d8a`.
- Current engine baselines remain honest failures:
  - dev: exact 0.1735849057, precision 1.0, recall 0.1735849057, F1 0.2958199357, abstention 0.7526881720.
  - test: exact 0.1635687732, precision 1.0, recall 0.1635687732, F1 0.2811501597, schema-held-out F1 0.2718446602, abstention 0.7696335079.
  - negative-pair, duplicate-source, and invalid-cardinality violations are all zero.
- Cardinality compares the engine-reported operation with the independently declared gold operation. Held-out schema metrics receive the split-derived schema set rather than a hard-coded family.
- External blind default remains `not_run`; supplying independent annotation and prediction JSONL now validates origin/schema/duplicates, executes automatic metrics, and emits annotation/prediction hashes.

## TDD and verification evidence

- Original RED: 6 failed because both v2 builders/evaluators were absent.
- Review-correction tag RED: 6 failed / 2 passed, covering old-gold dependency, overwrite protection, complete hash contract, manifest counts, duplicates/references/trace schema, exact trace/scope sets, and tag definitions.
- Review-correction mapping RED: 10 failed / 4 passed, covering normalized/subsequence leakage, wrong/shared no-match, actual variety/held-out derivation, unique negative counts, cardinality, held-out derivation, and executable blind evaluation.
- Final tag-v2 module: 11/11 passed.
- Final mapping-v2 module: 16/16 passed.
- Combined tag/mapping/candidate/global-assignment/pair-feature/gate regression: 52/52 passed.
- Builders reproduce frozen files byte-for-byte in temporary directories; dev/test evaluators and external `not_run` runner executed successfully.
- Fresh evaluator outputs were SHA-identical to all four frozen reports: tag `8cc7ac9beee0fd2463598236e37aceb31faa7983bf0f43075c2e6fbcbc15dde8`, dev `5dbac4780865d4373901c3c329143379587a66c8f4e9c98f6129c80b1fea51bb`, test `cefa043ddd69f019f9555d873cad2e68dace596e8005a2e59e5e1bd432833e72`, and external-blind `fb8b7ed542abdd0bf8e00e34aa09ca16e93ac7ed596aeaa893f5f6b3ba26dc43`.
- Ruff passed for all new/changed scripts and tests. `git diff --check` passed for both freeze scopes.
