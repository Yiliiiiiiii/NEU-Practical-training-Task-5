import re

from app.schemas.canonical import CanonicalModel
from app.schemas.chunks import ChunksJSON
from app.schemas.content import ContentJSON
from app.schemas.reports import ConsistencyCheck, ConsistencyReport, ReportIssue


def validate_consistency(
    task_id: str,
    content_json: ContentJSON,
    content_md: str,
    chunks: ChunksJSON,
    canonical: CanonicalModel,
) -> ConsistencyReport:
    checks: list[ConsistencyCheck] = []

    canonical_order = [b.block_id for b in canonical.blocks]
    canonical_block_ids = set(canonical_order)
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

    if json_block_ids != canonical_order:
        checks.append(ConsistencyCheck(
            check_name="block_order_consistency",
            passed=False,
            severity="critical",
            message="content.json block order does not match canonical block order",
            details={"expected": canonical_order, "actual": json_block_ids},
        ))
    else:
        checks.append(ConsistencyCheck(
            check_name="block_order_consistency",
            passed=True,
            severity="critical",
            message="content.json block order matches canonical block order",
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

    markdown_order = re.findall(r"<!--\s*block_id:\s*([^|\s>-]+)", content_md)
    if markdown_order and markdown_order != canonical_order:
        checks.append(ConsistencyCheck(
            check_name="markdown_block_order_consistency",
            passed=False,
            severity="critical",
            message="content.md block order does not match canonical block order",
            details={"expected": canonical_order, "actual": markdown_order},
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

    errors: list[ReportIssue] = []
    warnings: list[ReportIssue] = []
    for c in checks:
        if not c.passed and c.severity == "critical":
            errors.append(ReportIssue(
                level="error",
                code=c.check_name,
                message=c.message or c.check_name,
            ))
        elif not c.passed:
            warnings.append(ReportIssue(
                level="warning",
                code=c.check_name,
                message=c.message or c.check_name,
            ))

    passed = len(errors) == 0

    return ConsistencyReport(
        task_id=task_id,
        passed=passed,
        checks=checks,
        errors=errors,
        warnings=warnings,
    )
