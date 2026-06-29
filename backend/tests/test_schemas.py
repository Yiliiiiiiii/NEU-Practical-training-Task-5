import pytest
from pydantic import ValidationError


def test_uir_document_parses_core_shape():
    from app.schemas.uir import UIRDocument

    document = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc_001",
            "source": {
                "source_type": "normalized_uir",
                "source_name": "general_doc_001",
                "upstream_agents": ["parser", "cleaner", "normalizer"],
            },
            "metadata": {"title": "测试文档", "author": "信息中心"},
            "blocks": [
                {
                    "block_id": "blk_001",
                    "type": "heading",
                    "level": 1,
                    "text": "测试文档",
                    "source_anchor": {"page": 1, "bbox": [0, 0, 100, 20]},
                    "attributes": {"section_no": "1"},
                }
            ],
            "assets": [
                {
                    "asset_id": "asset_001",
                    "type": "image",
                    "path": "assets/image_001.png",
                    "source_block_id": "blk_001",
                    "sha256": "abc",
                }
            ],
            "normalization_records": [{"entity_id": "ent_001", "block_id": "blk_001"}],
        }
    )

    assert document.doc_id == "doc_001"
    assert document.blocks[0].source_anchor is not None
    assert document.assets[0].source_block_id == "blk_001"


def test_uir_document_requires_doc_id():
    from app.schemas.uir import UIRDocument

    with pytest.raises(ValidationError):
        UIRDocument.model_validate({"uir_version": "1.0", "metadata": {}, "blocks": []})


def test_target_schema_requires_at_least_one_field():
    from app.schemas.target_schema import TargetSchema

    schema = TargetSchema.model_validate(
        {
            "schema_id": "schema_general_v1",
            "name": "通用文档",
            "version": "1.0.0",
            "description": "通用文档标准结构",
            "fields": [
                {
                    "field_id": "title",
                    "name": "title",
                    "display_name": "标题",
                    "type": "string",
                    "required": True,
                    "aliases": ["题名"],
                    "constraints": {"min_length": 1},
                }
            ],
            "json_schema": {
                "type": "object",
                "required": ["title"],
                "properties": {"title": {"type": "string"}},
            },
        }
    )

    assert schema.fields[0].field_id == "title"

    with pytest.raises(ValidationError):
        TargetSchema.model_validate(
            {
                "schema_id": "schema_empty",
                "name": "空 Schema",
                "version": "1.0.0",
                "fields": [],
                "json_schema": {"type": "object"},
            }
        )


def test_mapping_template_parses_rules_and_rejects_targetless_transform():
    from app.schemas.mapping_template import MappingTemplate

    template = MappingTemplate.model_validate(
        {
            "template_id": "tpl_general_v1",
            "schema_id": "schema_general_v1",
            "name": "通用映射模板",
            "version": "1.0.0",
            "aliases": {"title": ["标题", "题名"]},
            "regex_rules": [
                {
                    "target_field_id": "created_date",
                    "pattern": "(创建日期)[:：]\\s*(\\d{4}年\\d{1,2}月\\d{1,2}日)",
                    "group": 2,
                }
            ],
            "transform_rules": [
                {
                    "rule_id": "date_created",
                    "operation": "date_format",
                    "source_field": "metadata.创建日期",
                    "target_field_id": "created_date",
                    "params": {"output_format": "YYYY-MM-DD"},
                }
            ],
            "defaults": {"language": "zh-CN"},
            "enum_maps": {"doc_type": {"办法": "policy"}},
        }
    )

    assert template.aliases["title"] == ["标题", "题名"]
    assert template.transform_rules[0].target_field_id == "created_date"

    with pytest.raises(ValidationError):
        MappingTemplate.model_validate(
            {
                "template_id": "tpl_bad",
                "schema_id": "schema_general_v1",
                "name": "坏模板",
                "version": "1.0.0",
                "transform_rules": [{"rule_id": "bad", "operation": "rename"}],
            }
        )


def test_mapping_and_canonical_models_round_trip():
    from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
    from app.schemas.mapping import FieldCandidate, FieldMapping

    candidate = FieldCandidate.model_validate(
        {
            "candidate_id": "cand_001",
            "task_id": "task_001",
            "doc_id": "doc_001",
            "source_path": "metadata.title",
            "source_name": "title",
            "display_name": "标题",
            "value_sample": "测试文档",
            "inferred_type": "string",
            "source_blocks": ["blk_001"],
            "confidence": 0.95,
            "evidence": ["metadata key matched"],
        }
    )
    mapping = FieldMapping.model_validate(
        {
            "mapping_id": "map_001",
            "task_id": "task_001",
            "candidate_id": candidate.candidate_id,
            "source_field": {
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
            },
            "target_field_id": "title",
            "target_field_name": "title",
            "method": "exact_match",
            "confidence": 1.0,
            "status": "confirmed",
            "need_review": False,
            "evidence": ["source_name equals target field name"],
        }
    )
    canonical = CanonicalModel(
        canonical_version="1.0",
        task_id="task_001",
        doc_id="doc_001",
        schema_id="schema_general_v1",
        doc_meta={"title": "测试文档"},
        fields={
            "title": CanonicalField(
                value="测试文档",
                type="string",
                source_candidates=[candidate.candidate_id],
                source_blocks=["blk_001"],
            )
        },
        blocks=[
            CanonicalBlock(
                block_id="blk_001",
                type="heading",
                level=1,
                text="测试文档",
                source_blocks=["blk_001"],
                text_hash="sha256:abc",
            )
        ],
        assets=[],
    )

    assert mapping.status == "accepted"
    assert mapping.evidence[0].message == "source_name equals target field name"
    assert mapping.evidence_text == ["source_name equals target field name"]
    assert canonical.fields["title"].source_candidates == ["cand_001"]


def test_reports_package_review_snapshot_and_profile_models_parse():
    from app.schemas.output_profile import OutputProfile
    from app.schemas.package import Manifest, ManifestFile, OutputPackageMetadata
    from app.schemas.reports import (
        ConsistencyCheck,
        ConsistencyReport,
        MappingReport,
        ValidationReport,
    )
    from app.schemas.review import ReviewRecord
    from app.schemas.run_snapshot import ExecutionSnapshot

    mapping_report = MappingReport(
        task_id="task_001",
        schema_id="schema_general_v1",
        summary={
            "target_fields": 1,
            "mapped_fields": 1,
            "unmapped_required_fields": 0,
            "review_required": 0,
            "average_confidence": 1.0,
        },
        mappings=[],
        unmapped=[],
        review_required_items=[],
    )
    validation_report = ValidationReport(
        task_id="task_001",
        schema_id="schema_general_v1",
        passed=True,
        summary={"error_count": 0, "warning_count": 0},
        issues=[],
    )
    consistency_report = ConsistencyReport(
        task_id="task_001",
        passed=True,
        checks=[
            ConsistencyCheck(
                check_name="chunks_source_blocks_backlink",
                passed=True,
                details={"missing_block_ids": []},
            )
        ],
        errors=[],
        warnings=[],
    )
    manifest = Manifest(
        manifest_version="1.1",
        package_id="pkg_001",
        package_version="1.0.0",
        task_id="task_001",
        doc_id="doc_001",
        created_at="2026-06-22T10:00:00+08:00",
        files=[
            ManifestFile(
                path="content.json",
                required=True,
                media_type="application/json",
                sha256="abc",
                bytes=123,
            )
        ],
        generator={"name": "SchemaPack Agent", "version": "0.1.0"},
    )
    package = OutputPackageMetadata(
        package_id="pkg_001",
        task_id="task_001",
        doc_id="doc_001",
        schema_id="schema_general_v1",
        template_id="tpl_general_v1",
        package_version="1.0.0",
        zip_path="storage/packages/pkg_001/standard_package.zip",
        status="completed",
        sha256="zip_sha256",
        created_at="2026-06-22T10:00:00+08:00",
    )
    review = ReviewRecord(
        review_id="rev_001",
        task_id="task_001",
        mapping_id="map_001",
        candidate_id="cand_001",
        old_target_field_id="summary",
        new_target_field_id="abstract",
        reviewer="human",
        decision="modified",
        comment="人工修正",
        created_at="2026-06-22T10:05:00+08:00",
    )
    snapshot = ExecutionSnapshot(
        snapshot_version="1.0",
        task_id="task_001",
        parent_task_id=None,
        input_hash="sha256:abc",
        schema_ref={"schema_id": "schema_general_v1", "version": "1.0.0"},
        template_ref={"template_id": "tpl_general_v1", "version": "1.0.0"},
        options={"chunk_size": 800},
        engine_version="0.1.0",
        build_commit=None,
        prompt_version="field_mapping_v1",
        model={"mode": "mock", "name": "mock", "temperature": 0},
        confirmed_mapping_ids=["map_001"],
        created_at="2026-06-22T10:00:00+08:00",
    )
    profile = OutputProfile(
        profile_id="general_json_v1",
        format="json",
        source_path="$.data",
        file_name="exports/general.json",
        field_order=["title", "author"],
    )

    assert mapping_report.summary["mapped_fields"] == 1
    assert validation_report.passed is True
    assert consistency_report.checks[0].passed is True
    assert manifest.files[0].path == "content.json"
    assert package.status == "completed"
    assert review.decision == "modified"
    assert snapshot.model["mode"] == "mock"
    assert profile.format == "json"
