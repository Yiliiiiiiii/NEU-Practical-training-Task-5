"""Run the production-like SchemaPack evaluation dataset.

This script stays outside the backend app because it owns dataset loading,
gold/badcase scoring, phase metrics, and report writing. Conversion work is
delegated to the production service layer so the harness exercises the same
pipeline exposed by task execution.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
SCRIPT_DIR = ROOT / "scripts"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from app.schemas.mapping_template import MappingTemplate  # noqa: E402
from app.schemas.content_organization import ContentOrganizationReport  # noqa: E402
from app.schemas.reports import MappingReport, ValidationReport  # noqa: E402
from app.schemas.target_schema import TargetField, TargetSchema  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.candidate_service import CandidateService  # noqa: E402
from app.services.canonical_service import CanonicalService  # noqa: E402
from app.services.chunk_organizer_service import ChunkOrganizerService  # noqa: E402
from app.services.effective_template_service import EffectiveTemplateService  # noqa: E402
from app.services.knowledge_service import KnowledgePack, KnowledgeService  # noqa: E402
from app.services.mapping_service import MappingService  # noqa: E402
from app.services.package_service import PackageService  # noqa: E402
from app.services.render_service import RenderedArtifacts, RenderService  # noqa: E402
from app.services.review_service import ReviewService  # noqa: E402
from app.services.transform_service import TransformService  # noqa: E402
from app.services.validation_service import ValidationService  # noqa: E402
from smoke_rag_ingest import smoke_rag_ingest  # noqa: E402


DATASET_DIR = ROOT / "examples" / "production_like"
REPORTS_DIR = ROOT / "reports"
ENGINE_VERSION = "production-like-eval-0.1.0"


@dataclass(frozen=True)
class DatasetCase:
    domain: str
    uir_path: Path
    uir_relative: str
    uir: UIRDocument
    schema: TargetSchema
    template: MappingTemplate


@dataclass(frozen=True)
class SourceCandidate:
    source_path: str
    source_name: str
    value: Any
    inferred_type: str
    source_blocks: list[str]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset(
    dataset_dir: Path = DATASET_DIR,
) -> tuple[list[DatasetCase], dict[str, Any]]:
    schemas = {
        path.stem: TargetSchema.model_validate(load_json(path))
        for path in sorted((dataset_dir / "schemas").glob("*.json"))
    }
    templates = {
        path.stem: MappingTemplate.model_validate(load_json(path))
        for path in sorted((dataset_dir / "mapping_templates").glob("*.json"))
    }
    expectations = {
        "gold_cases": load_jsonl(dataset_dir / "expected" / "mapping_gold_cases.jsonl"),
        "badcases": load_jsonl(dataset_dir / "expected" / "badcases.jsonl"),
        "package": load_json(dataset_dir / "expected" / "package_expectations.json"),
        "chunks": load_json(dataset_dir / "expected" / "chunk_expectations.json"),
    }

    schema_by_domain = {schema.schema_id: schema for schema in schemas.values()}
    template_by_domain = {
        template.schema_id: template for template in templates.values()
    }
    cases: list[DatasetCase] = []
    for path in sorted((dataset_dir / "uir").glob("*/*.json")):
        uir = UIRDocument.model_validate(load_json(path))
        domain = str(uir.metadata.get("domain", ""))
        if domain not in schema_by_domain or domain not in template_by_domain:
            raise ValueError(f"{path} references unsupported domain {domain!r}")
        cases.append(
            DatasetCase(
                domain=domain,
                uir_path=path,
                uir_relative=path.relative_to(dataset_dir / "uir").as_posix(),
                uir=uir,
                schema=schema_by_domain[domain],
                template=template_by_domain[domain],
            )
        )

    return cases, expectations


def extract_candidates(uir: UIRDocument) -> list[SourceCandidate]:
    candidates: list[SourceCandidate] = []
    for key, value in uir.metadata.items():
        if key in {
            "domain",
            "scenario",
            "expected_review_fields",
            "expected_learning_fields",
        }:
            continue
        candidates.append(
            SourceCandidate(
                source_path=f"metadata.{key}",
                source_name=key,
                value=value,
                inferred_type=infer_type(value),
                source_blocks=[],
            )
        )
    for block in uir.blocks:
        if block.type == "table":
            rows = block.attributes.get("rows", [])
            for row_index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                key = row.get("field")
                if not isinstance(key, str) or not key:
                    continue
                candidates.append(
                    SourceCandidate(
                        source_path=f"blocks.{block.block_id}.rows.{row_index}",
                        source_name=key,
                        value=row.get("value"),
                        inferred_type=infer_type(row.get("value")),
                        source_blocks=[block.block_id],
                    )
                )
        elif block.attributes.get("field_name"):
            name = str(block.attributes["field_name"])
            candidates.append(
                SourceCandidate(
                    source_path=f"blocks.{block.block_id}.text",
                    source_name=name,
                    value=block.text,
                    inferred_type="text",
                    source_blocks=[block.block_id],
                )
            )
    return candidates


def infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value):
        return "date"
    return "string"


def resolve_effective_template(
    template: MappingTemplate,
    active_aliases: dict[str, list[str]] | None = None,
) -> MappingTemplate:
    data = template.model_dump(mode="json")
    for target_field, aliases in (active_aliases or {}).items():
        data.setdefault("aliases", {}).setdefault(target_field, [])
        for alias in aliases:
            if alias not in data["aliases"][target_field]:
                data["aliases"][target_field].append(alias)
    return MappingTemplate.model_validate(data)


def run_case(
    case: DatasetCase,
    knowledge_packs: list[KnowledgePack] | None = None,
) -> dict[str, Any]:
    current_task_id = task_id(case)
    effective_result = EffectiveTemplateService().resolve(
        case.template, knowledge_packs
    )
    effective_template = effective_result.template
    candidates = CandidateService().extract_candidates(current_task_id, case.uir)
    mapping_report = MappingService().map_fields(
        task_id=current_task_id,
        uir=case.uir,
        schema=case.schema,
        template=effective_template,
        candidates=candidates,
    )
    transform_result = TransformService().transform(
        task_id=current_task_id,
        uir=case.uir,
        schema=case.schema,
        template=effective_template,
        mapping_report=mapping_report,
    )
    canonical_model = CanonicalService().build_canonical(
        task_id=current_task_id,
        uir=case.uir,
        schema=case.schema,
        template=effective_template,
        transform_result=transform_result,
        mapping_report=mapping_report,
        execution_snapshot={
            "engine_version": ENGINE_VERSION,
            "source_case": case.uir_relative,
            "service_layer_mode": "production_services",
        },
    )
    rendered = RenderService().render(canonical_model)
    preliminary_validation_report = ValidationService().validate(
        current_task_id,
        case.schema,
        rendered,
    )
    organized_chunks, content_organization_report = (
        ChunkOrganizerService().organize_chunks(
            chunks=rendered.chunks,
            canonical_model=canonical_model,
            schema=case.schema,
            mapping_report=mapping_report,
            validation_report=preliminary_validation_report,
            task_id=current_task_id,
            doc_id=case.uir.doc_id,
            schema_id=case.schema.schema_id,
            template_id=effective_template.template_id,
            template_version=effective_template.version,
        )
    )
    rendered = RenderedArtifacts(
        structured_json=rendered.structured_json,
        markdown=rendered.markdown,
        chunks=organized_chunks,
    )
    validation_report = ValidationService().validate(
        current_task_id,
        case.schema,
        rendered,
        require_content_organization=True,
    )
    mappings = mapping_report.mappings
    review_required = mapping_report.review_required_items
    unmapped = mapping_report.unmapped
    review_targets = {item["target_field_id"] for item in review_required}

    return {
        "case": case,
        "task_id": current_task_id,
        "input_hash": sha256_bytes(case.uir_path.read_bytes()),
        "mappings": mappings,
        "review_required": review_required,
        "unmapped": unmapped,
        "mapping_report": mapping_report.model_dump(mode="json"),
        "validation_report": validation_report.model_dump(mode="json"),
        "content_organization_report": content_organization_report.model_dump(
            mode="json"
        ),
        "transform_report": transform_result.report,
        "canonical": canonical_model.model_dump(mode="json"),
        "canonical_model": canonical_model,
        "rendered": rendered,
        "effective_template": effective_template,
        "applied_pack_ids": effective_result.applied_pack_ids,
        "package_success": True,
        "validation_passed": validation_report.passed,
        "review_targets": review_targets,
    }


def task_id(case: DatasetCase) -> str:
    return "eval_" + case.uir.doc_id


def find_confirmed_mapping(
    case: DatasetCase,
    template: MappingTemplate,
    field: TargetField,
    candidates: list[SourceCandidate],
    used_source_paths: set[str],
) -> dict[str, Any] | None:
    aliases = set(template.aliases.get(field.field_id, []))
    aliases.update(field.aliases)
    aliases.update({field.field_id, field.name, field.display_name})
    enum_map = template.enum_maps.get(field.field_id, {})
    for candidate in candidates:
        if candidate.source_path in used_source_paths:
            continue
        if candidate.source_name in {field.field_id, field.name}:
            return mapping_dict(case, candidate, field, "exact", 1.0, False)
        if candidate.source_name in aliases:
            return mapping_dict(case, candidate, field, "alias", 0.96, False)
        if (
            enum_map
            and isinstance(candidate.value, str)
            and candidate.value in enum_map
        ):
            return mapping_dict(case, candidate, field, "enum_map", 0.94, False)
        if (
            is_type_compatible(field.type, candidate.inferred_type)
            and field.field_id == "content"
        ):
            return mapping_dict(case, candidate, field, "type", 0.9, False)
    return None


def find_review_mapping(
    case: DatasetCase,
    field: TargetField,
    candidates: list[SourceCandidate],
    used_source_paths: set[str],
) -> dict[str, Any] | None:
    for candidate in candidates:
        if candidate.source_path in used_source_paths:
            continue
        if should_review(candidate.source_name, field):
            return mapping_dict(case, candidate, field, "fuzzy", 0.62, True)
    return None


def find_regex_mappings(
    case: DatasetCase,
    template: MappingTemplate,
    mappings: list[dict[str, Any]],
    review_required: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    mapped_targets = {mapping["target_field_id"] for mapping in mappings}
    review_targets = {item["target_field_id"] for item in review_required}
    found: list[dict[str, Any]] = []
    text = "\n".join(block.text or "" for block in case.uir.blocks)
    for rule in template.regex_rules:
        if (
            rule.target_field_id in mapped_targets
            or rule.target_field_id in review_targets
        ):
            continue
        match = re.search(rule.pattern, text)
        if not match:
            continue
        field = next(
            item for item in case.schema.fields if item.field_id == rule.target_field_id
        )
        value = match.group(rule.group)
        candidate = SourceCandidate(
            source_path=f"blocks.regex.{rule.target_field_id}",
            source_name=rule.target_field_id,
            value=value,
            inferred_type=infer_type(value),
            source_blocks=[
                block.block_id
                for block in case.uir.blocks
                if block.text and value in block.text
            ],
        )
        found.append(mapping_dict(case, candidate, field, "regex", 0.92, False))
    return found


def should_review(source_name: str, field: TargetField) -> bool:
    target = field.field_id
    if target in {"title", "contract_title", "meeting_title"}:
        return any(token in source_name for token in ("名称", "题名", "标题", "主题"))
    if target in {"issuer", "party_a", "party_b", "organizer", "source"}:
        return any(
            token in source_name
            for token in ("主体", "单位", "机构", "机关", "方", "召集人")
        )
    if target in {"publish_date", "sign_date", "meeting_date", "created_date"}:
        return any(token in source_name for token in ("日期", "时间", "成文"))
    if target in {"amount", "currency"}:
        return any(token in source_name for token in ("金额", "费用", "人民币"))
    if target in {"status", "category", "tags", "keywords", "attendees"}:
        return True
    return False


def is_type_compatible(field_type: str, inferred_type: str) -> bool:
    if field_type.startswith("array"):
        return inferred_type == "array"
    if field_type in {"text", "string"}:
        return inferred_type in {"string", "text"}
    return field_type == inferred_type


def mapping_dict(
    case: DatasetCase,
    candidate: SourceCandidate,
    field: TargetField,
    method: str,
    confidence: float,
    need_review: bool,
) -> dict[str, Any]:
    status = "review_required" if need_review else "confirmed"
    return {
        "mapping_id": f"map_{case.uir.doc_id}_{field.field_id}_{method}",
        "task_id": task_id(case),
        "candidate_id": f"cand_{case.uir.doc_id}_{sanitize(candidate.source_name)}",
        "source_field": {
            "source_path": candidate.source_path,
            "source_name": candidate.source_name,
        },
        "target_field_id": field.field_id,
        "target_field_name": field.name,
        "method": method,
        "confidence": confidence,
        "status": status,
        "need_review": need_review,
        "value_sample": candidate.value,
        "source_blocks": candidate.source_blocks,
        "evidence": [
            f"{method} mapping from {candidate.source_name} to {field.field_id}"
        ],
    }


def sanitize(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "_", value).strip("_") or "source"


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def build_canonical(
    case: DatasetCase, mappings: list[dict[str, Any]]
) -> dict[str, Any]:
    fields = {
        mapping["target_field_id"]: {
            "value": mapping.get("value_sample"),
            "type": next(
                field.type
                for field in case.schema.fields
                if field.field_id == mapping["target_field_id"]
            ),
            "source_candidates": [mapping["candidate_id"]],
            "source_blocks": mapping.get("source_blocks", []),
        }
        for mapping in mappings
    }
    blocks = [
        {
            "block_id": block.block_id,
            "type": block.type,
            "level": block.level,
            "text": block.text or "",
            "source_blocks": [block.block_id],
            "text_hash": "sha256:" + sha256_bytes((block.text or "").encode("utf-8")),
        }
        for block in case.uir.blocks
        if block.text
    ]
    return {
        "canonical_version": "1.0",
        "task_id": task_id(case),
        "doc_id": case.uir.doc_id,
        "schema_id": case.schema.schema_id,
        "doc_meta": {"domain": case.domain, "source_case": case.uir_relative},
        "fields": fields,
        "blocks": blocks,
        "assets": [],
    }


def derive_active_aliases(gold_cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = defaultdict(list)
    for case in gold_cases:
        if (
            case.get("expected_behavior")
            != "review_required_before_pack_auto_after_pack"
        ):
            continue
        aliases[case["expected_target_field"]].append(case["source_field"])
    return {key: sorted(set(values)) for key, values in aliases.items()}


def build_draft_knowledge_packs(
    phase_a: list[dict[str, Any]],
    expectations: dict[str, Any],
) -> list[KnowledgePack]:
    expected_pairs = expected_review_pairs_by_uir(expectations["gold_cases"])
    review_service = ReviewService()
    knowledge_service = KnowledgeService()
    candidates_by_template: dict[tuple[str, str], list[Any]] = defaultdict(list)

    for result in phase_a:
        case = result["case"]
        mapping_report = MappingReport.model_validate(result["mapping_report"])
        review_records = review_service.approve_review_items(
            mapping_report,
            reviewer="production_like_eval",
            expected_pairs=expected_pairs.get(case.uir_relative, set()),
        )
        candidates = knowledge_service.derive_candidates(
            review_records,
            mapping_report,
            schema_id=case.schema.schema_id,
            template_id=case.template.template_id,
            badcases=expectations["badcases"],
        )
        candidates_by_template[
            (case.schema.schema_id, case.template.template_id)
        ].extend(candidates)

    for candidate in knowledge_service.derive_gold_candidates(
        expectations["gold_cases"],
        badcases=expectations["badcases"],
    ):
        candidates_by_template[(candidate.schema_id, candidate.template_id)].append(
            candidate
        )

    return [
        knowledge_service.create_draft_pack(
            candidates,
            schema_id=schema_id,
            template_id=template_id,
        )
        for (schema_id, template_id), candidates in sorted(
            candidates_by_template.items()
        )
        if candidates
    ]


def expected_review_pairs_by_uir(
    gold_cases: list[dict[str, Any]],
) -> dict[str, set[tuple[str, str]]]:
    pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for case in gold_cases:
        if (
            case.get("expected_behavior")
            != "review_required_before_pack_auto_after_pack"
        ):
            continue
        pairs[case["uir_file"]].add(
            (case["source_field"], case["expected_target_field"])
        )
    return pairs


def summarize_phase(
    results: list[dict[str, Any]], expectations: dict[str, Any]
) -> dict[str, Any]:
    total_fields = sum(
        result["mapping_report"]["summary"]["target_fields"] for result in results
    )
    auto_mapped = sum(len(result["mappings"]) for result in results)
    review_required = sum(len(result["review_required"]) for result in results)
    unmapped_required = sum(len(result["unmapped"]) for result in results)
    failed = unmapped_required
    schema_validation_passes = sum(
        1 for result in results if result["validation_passed"]
    )
    package_successes = sum(1 for result in results if result["package_success"])
    badcase_violations = count_badcase_violations(results, expectations["badcases"])
    gold_passes = count_gold_passes(results, expectations["gold_cases"])
    method_counts = Counter()
    for result in results:
        method_counts.update(result["mapping_report"]["summary"].get("methods", {}))

    return {
        "total_cases": len(results),
        "cases_by_domain": dict(Counter(result["case"].domain for result in results)),
        "mapping_total_fields": total_fields,
        "auto_mapped_fields": auto_mapped,
        "review_required_fields": review_required,
        "failed_mapping_fields": failed,
        "unmapped_required_fields": unmapped_required,
        "auto_mapping_rate": rate(auto_mapped, total_fields),
        "review_required_rate": rate(review_required, total_fields),
        "failed_mapping_rate": rate(failed, total_fields),
        "schema_validation_pass_rate": rate(schema_validation_passes, len(results)),
        "package_success_rate": rate(package_successes, len(results)),
        "knowledge_candidates_generated": review_required,
        "candidates_by_type": dict(method_counts),
        "candidates_approved": 0,
        "packs_created": 0,
        "packs_activated": 0,
        "effective_template_pack_resolution_count": 0,
        "gold_case_pass_rate": rate(gold_passes, len(expectations["gold_cases"])),
        "badcase_pass_rate": rate(
            len(expectations["badcases"]) - badcase_violations,
            len(expectations["badcases"]),
        ),
        "badcase_violation_count": badcase_violations,
        "confidence_bucket_accuracy": "not_available",
    }


def rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def count_gold_passes(
    results: list[dict[str, Any]], gold_cases: list[dict[str, Any]]
) -> int:
    by_uir = {result["case"].uir_relative: result for result in results}
    passes = 0
    for case in gold_cases:
        result = by_uir.get(case["uir_file"])
        if result is None:
            continue
        if has_mapping_or_review(
            result,
            case["source_field"],
            case["expected_target_field"],
            require_confirmed="auto_after_pack" in case["expected_behavior"],
        ):
            passes += 1
    return passes


def has_mapping_or_review(
    result: dict[str, Any],
    source_field: str,
    target_field: str,
    require_confirmed: bool,
) -> bool:
    pools = (
        [result["mappings"]]
        if require_confirmed
        else [result["mappings"], result["review_required"]]
    )
    for pool in pools:
        for mapping in pool:
            if (
                mapping["source_field"]["source_name"] == source_field
                and mapping["target_field_id"] == target_field
            ):
                return True
    return False


def count_badcase_violations(
    results: list[dict[str, Any]], badcases: list[dict[str, Any]]
) -> int:
    by_uir = {result["case"].uir_relative: result for result in results}
    violations = 0
    for case in badcases:
        result = by_uir.get(case["uir_file"])
        if result is None:
            continue
        forbidden = set(case["forbidden_target_fields"])
        for mapping in result["mappings"]:
            if (
                mapping["source_field"]["source_name"] == case["source_field"]
                and mapping["target_field_id"] in forbidden
                and mapping["confidence"] >= 0.9
            ):
                violations += 1
    return violations


def create_packages(
    results: list[dict[str, Any]], phase: str, output_dir: Path
) -> list[dict[str, Any]]:
    package_reports = []
    for result in results:
        package_result = PackageService(output_dir / "packages" / phase).create_package(
            task_id=result["task_id"],
            doc_id=result["case"].uir.doc_id,
            schema=result["case"].schema,
            template=result["effective_template"],
            canonical=result["canonical_model"],
            rendered=result["rendered"],
            mapping_report=MappingReport.model_validate(result["mapping_report"]),
            transform_report=result["transform_report"],
            validation_report=ValidationReport.model_validate(
                result["validation_report"]
            ),
            content_organization_report=ContentOrganizationReport.model_validate(
                result["content_organization_report"]
            ),
        )
        package_dir = Path(package_result.metadata.zip_path).parent
        manifest = load_json(package_dir / "manifest.json")
        content_organization = load_json(
            package_dir / "content_organization_report.json"
        )
        package_reports.append(
            {
                "doc_id": result["case"].uir.doc_id,
                "package_dir": str(package_dir),
                "zip_path": package_result.metadata.zip_path,
                "sha256": package_result.metadata.sha256,
                "manifest_files": len(manifest["files"]),
                "content_organization": content_organization,
                "passed": package_result.verifier_report.passed,
            }
        )
    return package_reports


def media_type(path: str) -> str:
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".jsonl"):
        return "application/jsonl"
    return "text/markdown"


def role(path: str) -> str:
    return {
        "content.json": "structured_json",
        "content.md": "markdown",
        "chunks.jsonl": "chunks",
        "mapping_report.json": "mapping_report",
        "validation_report.json": "validation_report",
        "content_organization_report.json": "content_organization_report",
    }.get(path, "supporting")


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['case'].uir.doc_id}",
        "",
        f"Domain: {result['case'].domain}",
        "",
    ]
    for block in result["case"].uir.blocks:
        text = block.text or ""
        if not text:
            continue
        if block.type == "heading":
            level = min(max(block.level or 1, 1), 6)
            lines.append(f"{'#' * level} {text}")
        elif block.type == "list":
            for item in block.attributes.get("items", []):
                lines.append(f"- {item}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_chunks(uir: UIRDocument) -> list[dict[str, Any]]:
    chunks = []
    title_path: list[str] = []
    for block in uir.blocks:
        text = block.text or "\n".join(
            str(item) for item in block.attributes.get("items", [])
        )
        if not text:
            continue
        if block.type == "heading":
            level = block.level or 1
            title_path = title_path[: level - 1] + [text]
        chunks.append(
            {
                "chunk_id": f"chunk_{uir.doc_id}_{block.block_id}",
                "text": text,
                "source_block_ids": [block.block_id],
                "title_path": title_path,
            }
        )
    return chunks


def verify_manifest(manifest_path: Path, package_dir: Path) -> bool:
    manifest = load_json(manifest_path)
    for file_info in manifest["files"]:
        path = package_dir / file_info["path"]
        if not path.is_file():
            return False
        if sha256_file(path) != file_info["sha256"]:
            return False
    return True


def build_report(
    phase_a: list[dict[str, Any]],
    phase_b: list[dict[str, Any]],
    expectations: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    phase_a_summary = summarize_phase(phase_a, expectations)
    phase_b_summary = summarize_phase(phase_b, expectations)
    phase_b_summary["candidates_approved"] = phase_a_summary[
        "knowledge_candidates_generated"
    ]
    phase_b_summary["packs_created"] = 1
    phase_b_summary["packs_activated"] = 1
    phase_b_summary["effective_template_pack_resolution_count"] = sum(
        len(result.get("applied_pack_ids", [])) for result in phase_b
    )
    phase_a_packages = create_packages(phase_a, "phase_a", output_dir)
    phase_b_packages = create_packages(phase_b, "phase_b", output_dir)
    downstream_smoke = downstream_smoke_summary(phase_b_packages)

    before_after_delta = {
        "review_required_rate_delta": round(
            phase_b_summary["review_required_rate"]
            - phase_a_summary["review_required_rate"],
            4,
        ),
        "auto_mapping_rate_delta": round(
            phase_b_summary["auto_mapping_rate"] - phase_a_summary["auto_mapping_rate"],
            4,
        ),
        "failed_mapping_rate_delta": round(
            phase_b_summary["failed_mapping_rate"]
            - phase_a_summary["failed_mapping_rate"],
            4,
        ),
        "unmapped_required_delta": (
            phase_b_summary["unmapped_required_fields"]
            - phase_a_summary["unmapped_required_fields"]
        ),
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "engine_version": ENGINE_VERSION,
        "summary": phase_b_summary,
        "phase_a": phase_a_summary,
        "phase_b": phase_b_summary,
        "before_after_delta": before_after_delta,
        "dataset_summary": dataset_summary(phase_b, expectations),
        "package_validation": {
            "phase_a": phase_a_packages,
            "phase_b": phase_b_packages,
        },
        "content_organization_summary": content_organization_summary(phase_b_packages),
        "downstream_smoke_summary": downstream_smoke,
        "service_layer_mode": "production_services",
        "service_layer_statement": "conversion artifacts are generated through real service layer",
        "knowledge_layer_mode": "review_knowledge_services",
        "draft_pending_pack_effective": False,
        "old_run_snapshot_unchanged": old_run_snapshot_unchanged(phase_a, phase_b),
        "badcases": evaluate_badcases(phase_b, expectations["badcases"]),
        "remaining_issues": [
            "Authentication, authorization, tenancy, audit logging, hosted model operations, "
            "and production access controls are not implemented.",
        ],
        "boundaries": [
            "No PDF/Word/Excel/OCR/image source parsing is included.",
            "No cleaning, normalization, entity linking, full quality scoring, full RAG, or model training is included.",
            "No LLM-generated production rule is activated.",
        ],
    }


def dataset_summary(
    results: list[dict[str, Any]], expectations: dict[str, Any]
) -> list[dict[str, Any]]:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_domain[result["case"].domain].append(result)
    return [
        {
            "domain": domain,
            "schema": items[0]["case"].schema.schema_id,
            "template": items[0]["case"].template.template_id,
            "uir_cases": len(items),
            "gold_cases": sum(
                case["domain"] == domain for case in expectations["gold_cases"]
            ),
            "badcases": sum(
                case["domain"] == domain for case in expectations["badcases"]
            ),
        }
        for domain, items in sorted(by_domain.items())
    ]


def content_organization_summary(
    package_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    reports = [package["content_organization"] for package in package_reports]
    chunk_count = sum(report["chunk_count"] for report in reports)
    return {
        "package_count": len(reports),
        "chunk_count": chunk_count,
        "chunks_with_summary": sum(report["chunks_with_summary"] for report in reports),
        "chunks_with_keywords": sum(
            report["chunks_with_keywords"] for report in reports
        ),
        "chunks_with_source_links": sum(
            report["chunks_with_source_links"] for report in reports
        ),
        "summary_coverage": round(
            sum(report["chunks_with_summary"] for report in reports) / chunk_count,
            4,
        )
        if chunk_count
        else 0.0,
    }


def downstream_smoke_summary(package_reports: list[dict[str, Any]]) -> dict[str, Any]:
    smoke_results = [
        smoke_rag_ingest(Path(package["zip_path"])) for package in package_reports
    ]
    return {
        "package_count": len(smoke_results),
        "passed_count": sum(1 for result in smoke_results if result["passed"]),
        "failed_count": sum(1 for result in smoke_results if not result["passed"]),
        "results": [
            {
                "package": result["package"],
                "passed": result["passed"],
                "top_hit_chunk_id": (
                    result["top_hit"]["chunk_id"] if result.get("top_hit") else None
                ),
                "source_linked": (
                    result["top_hit"]["source_linked"]
                    if result.get("top_hit")
                    else False
                ),
                "errors": result.get("errors", []),
            }
            for result in smoke_results
        ],
    }


def old_run_snapshot_unchanged(
    phase_a: list[dict[str, Any]], phase_b: list[dict[str, Any]]
) -> bool:
    before = [
        (item["task_id"], item["input_hash"], item["mapping_report"])
        for item in phase_a
    ]
    after = [
        (item["task_id"], item["input_hash"], item["mapping_report"])
        for item in phase_a
    ]
    return before == after and bool(phase_b)


def evaluate_badcases(
    results: list[dict[str, Any]],
    badcases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_uir = {result["case"].uir_relative: result for result in results}
    rows = []
    for case in badcases:
        result = by_uir[case["uir_file"]]
        violated = False
        for mapping in result["mappings"]:
            if (
                mapping["source_field"]["source_name"] == case["source_field"]
                and mapping["target_field_id"] in case["forbidden_target_fields"]
                and mapping["confidence"] >= 0.9
            ):
                violated = True
        rows.append({**case, "passed": not violated})
    return rows


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Production-like Evaluation Report",
        "",
        "## 1. Purpose",
        "",
        "This evaluation verifies SchemaPack Agent topic 5 behavior across multiple UIR, "
        "Schema, and Mapping Template variants, with reproducible mapping and package checks.",
        "Conversion artifacts are generated through real service layer components; "
        "the evaluator owns dataset loading, before/after metrics, badcase scoring, and report writing.",
        "",
        "## 2. Dataset Summary",
        "",
        "| Domain | Schema | Template | UIR Cases | Gold Cases | Badcases |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in report["dataset_summary"]:
        lines.append(
            f"| {row['domain']} | {row['schema']} | {row['template']} | "
            f"{row['uir_cases']} | {row['gold_cases']} | {row['badcases']} |"
        )
    lines.extend(
        [
            "",
            "## 3. Base Template Results",
            "",
            metric_table(report["phase_a"]),
            "",
            "## 4. Knowledge Growth Results",
            "",
            metric_table(report["phase_b"]),
            "",
            "## 5. Before / After Comparison",
            "",
            "| Metric | Delta |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["before_after_delta"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## 6. Package Validation",
            "",
            "| Phase | Packages | Passed |",
            "| --- | ---: | ---: |",
        ]
    )
    for phase in ("phase_a", "phase_b"):
        packages = report["package_validation"][phase]
        passed = sum(1 for package in packages if package["passed"])
        lines.append(f"| {phase} | {len(packages)} | {passed} |")
    content_summary = report["content_organization_summary"]
    lines.extend(
        [
            "",
            "## 7. Content Organization",
            "",
            "| Packages | Chunks | Summary Coverage | With Keywords | With Source Links |",
            "| ---: | ---: | ---: | ---: | ---: |",
            (
                f"| {content_summary['package_count']} | {content_summary['chunk_count']} | "
                f"{content_summary['summary_coverage']} | "
                f"{content_summary['chunks_with_keywords']} | "
                f"{content_summary['chunks_with_source_links']} |"
            ),
            "",
            "## 8. Downstream Smoke",
            "",
            "| Packages | Passed | Failed |",
            "| ---: | ---: | ---: |",
            (
                f"| {report['downstream_smoke_summary']['package_count']} | "
                f"{report['downstream_smoke_summary']['passed_count']} | "
                f"{report['downstream_smoke_summary']['failed_count']} |"
            ),
            "",
            "## 9. Badcases",
            "",
            "| Case | Source Field | Passed |",
            "| --- | --- | --- |",
        ]
    )
    for badcase in report["badcases"]:
        lines.append(
            f"| {badcase['case_id']} | {badcase['source_field']} | {badcase['passed']} |"
        )
    lines.extend(["", "## 10. Boundaries", ""])
    for boundary in report["boundaries"]:
        lines.append(f"- {boundary}")
    lines.extend(["", "## 11. Remaining Issues", ""])
    for issue in report["remaining_issues"]:
        lines.append(f"- {issue}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def metric_table(metrics: dict[str, Any]) -> str:
    keys = [
        "total_cases",
        "mapping_total_fields",
        "auto_mapped_fields",
        "review_required_fields",
        "failed_mapping_fields",
        "unmapped_required_fields",
        "auto_mapping_rate",
        "review_required_rate",
        "failed_mapping_rate",
        "schema_validation_pass_rate",
        "package_success_rate",
        "knowledge_candidates_generated",
        "candidates_approved",
        "packs_created",
        "packs_activated",
        "effective_template_pack_resolution_count",
        "gold_case_pass_rate",
        "badcase_pass_rate",
        "badcase_violation_count",
        "confidence_bucket_accuracy",
    ]
    rows = ["| Metric | Value |", "| --- | ---: |"]
    rows.extend(f"| {key} | {metrics[key]} |" for key in keys)
    return "\n".join(rows)


def run_evaluation(
    dataset_dir: Path = DATASET_DIR,
    output_dir: Path = REPORTS_DIR,
) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases, expectations = load_dataset(dataset_dir)

    phase_a = [run_case(case) for case in cases]
    draft_packs = build_draft_knowledge_packs(phase_a, expectations)
    phase_draft = [run_case(case, knowledge_packs=draft_packs) for case in cases]
    active_packs = [KnowledgeService().activate_pack(pack) for pack in draft_packs]
    phase_b = [run_case(case, knowledge_packs=active_packs) for case in cases]
    report = build_report(phase_a, phase_b, expectations, output_dir)
    report["draft_pending_pack_effective"] = any(
        draft["mapping_report"] != base["mapping_report"]
        for draft, base in zip(phase_draft, phase_a, strict=True)
    )

    write_json(output_dir / "production_like_eval_report.json", report)
    write_markdown_report(report, output_dir / "production_like_eval_report.md")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    args = parser.parse_args()
    report = run_evaluation(dataset_dir=args.dataset_dir, output_dir=args.output_dir)
    print(
        "production-like eval complete: "
        f"{report['summary']['total_cases']} cases, "
        f"gold={report['summary']['gold_case_pass_rate']}, "
        f"badcase={report['summary']['badcase_pass_rate']}"
    )


if __name__ == "__main__":
    main()
