from app.schemas.canonical import CanonicalModel
from app.schemas.chunks import ChunksJSON
from app.schemas.content import ContentJSON
from app.schemas.reports import ConsistencyCheck, ConsistencyReport


def validate_consistency(
    task_id: str,
    content_json: ContentJSON,
    content_md: str,
    chunks: ChunksJSON,
    canonical: CanonicalModel,
) -> ConsistencyReport:
    checks: list[ConsistencyCheck] = []

    canonical_block_ids = {b.block_id for b in canonical.blocks}
    json_block_ids = [b.block_id for b in content_json.blocks]

    if set(json_block_ids) != canonical_block_ids:
        missing = canonical_block_ids - set(json_block_ids)
        extra = set(json_block_ids) - canonical_block_ids
        checks.append(ConsistencyCheck(
            check_name="block_id_coverage",
            passed=False,
            severity="critical",
            message=f"json blocks missing={missing}, extra={extra}",
        ))
    else:
        checks.append(ConsistencyCheck(
            check_name="block_id_coverage",
            passed=True,
            severity="critical",
            message="all canonical block_ids present in content.json",
        ))

    for block in content_json.blocks:
        if block.block_id not in canonical_block_ids:
            checks.append(ConsistencyCheck(
                check_name="block_id_backlink",
                passed=False,
                severity="critical",
                message=f"block '{block.block_id}' not in canonical",
            ))
            continue
        canonical_block = next(b for b in canonical.blocks if b.block_id == block.block_id)
        if block.text != canonical_block.text:
            checks.append(ConsistencyCheck(
                check_name="block_text_consistency",
                passed=False,
                severity="critical",
                message=f"block '{block.block_id}' text mismatch",
            ))

    for block_id in canonical_block_ids:
        if f"<!-- block_id: {block_id}" not in content_md:
            checks.append(ConsistencyCheck(
                check_name="markdown_block_annotation",
                passed=False,
                severity="critical",
                message=f"block '{block_id}' missing in markdown annotation",
            ))

    chunk_source_blocks: set[str] = set()
    for chunk in chunks.chunks:
        for sb in chunk.source_blocks:
            chunk_source_blocks.add(sb)

    orphan_blocks = chunk_source_blocks - canonical_block_ids
    if orphan_blocks:
        checks.append(ConsistencyCheck(
            check_name="chunk_source_blocks_backlink",
            passed=False,
            severity="critical",
            message=f"chunk source_blocks not in canonical: {orphan_blocks}",
        ))
    else:
        checks.append(ConsistencyCheck(
            check_name="chunk_source_blocks_backlink",
            passed=True,
            severity="critical",
            message="all chunk source_blocks link to canonical blocks",
        ))

    all_text = "\n".join(b.text for b in canonical.blocks if b.text)
    for chunk in chunks.chunks:
        for segment in chunk.text.split("\n"):
            segment = segment.strip()
            if segment and segment not in all_text:
                checks.append(ConsistencyCheck(
                    check_name="chunk_text_coverage",
                    passed=False,
                    severity="warning",
                    message=f"chunk '{chunk.chunk_id}' has text not in canonical",
                ))

    errors = []
    warnings = []
    for c in checks:
        if not c.passed and c.severity == "critical":
            errors.append(c)
        elif not c.passed:
            warnings.append(c)

    passed = len(errors) == 0

    return ConsistencyReport(
        task_id=task_id,
        passed=passed,
        checks=checks,
        errors=[],
        warnings=[],
    )
