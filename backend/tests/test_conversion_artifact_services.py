import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"
UIR_DIR = PRODUCTION_LIKE_DIR / "uir"


def load_uir(name: str):
    from app.schemas.uir import UIRDocument

    return UIRDocument.model_validate(json.loads((UIR_DIR / name).read_text(encoding="utf-8")))


def run_mapping(task_id: str, uir_name: str, schema_id: str, template_id: str):
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    uir = load_uir(uir_name)
    schema = SchemaService(SCHEMAS_DIR).load_schema(schema_id)
    template = TemplateService(TEMPLATES_DIR).load_template(template_id)
    candidates = CandidateService().extract_candidates(task_id, uir)
    mapping_report = MappingService().map_fields(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )
    return uir, schema, template, mapping_report


def test_transform_service_builds_structured_data_and_report():
    from app.services.transform_service import TransformService

    uir, schema, template, mapping_report = run_mapping(
        "task_policy_001",
        "policy/policy_001_standard.json",
        "policy_doc",
        "policy_doc_base_v1",
    )

    result = TransformService().transform(
        task_id="task_policy_001",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=mapping_report,
    )

    assert result.data["title"] == "数据资源共享管理办法"
    assert result.data["issuer"] == "市数据管理局"
    assert result.data["publish_date"] == "2024-03-12"
    assert result.data["doc_type"] == "measure"
    assert result.report["summary"]["transformed_fields"] >= 4
    assert result.report["errors"] == []


def test_transform_service_records_missing_required_error():
    from app.services.transform_service import TransformService

    uir, schema, template, mapping_report = run_mapping(
        "task_meeting_003",
        "meeting/meeting_003_missing_required.json",
        "meeting_doc",
        "meeting_doc_base_v1",
    )

    result = TransformService().transform(
        task_id="task_meeting_003",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=mapping_report,
    )

    assert "meeting_date" not in result.data
    assert any(error["field_id"] == "meeting_date" for error in result.report["errors"])


def test_canonical_and_render_services_preserve_sources_and_chunks():
    from app.services.canonical_service import CanonicalService
    from app.services.render_service import RenderService
    from app.services.transform_service import TransformService

    uir, schema, template, mapping_report = run_mapping(
        "task_general_001",
        "general/general_001_standard.json",
        "general_doc",
        "general_doc_base_v1",
    )
    uir.metadata["retrieved_at"] = "2026-07-10T00:00:00Z"
    uir.metadata["execution_snapshot"] = {"forged": True}
    transform_result = TransformService().transform(
        task_id="task_general_001",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=mapping_report,
    )
    canonical = CanonicalService().build_canonical(
        task_id="task_general_001",
        uir=uir,
        schema=schema,
        template=template,
        transform_result=transform_result,
        mapping_report=mapping_report,
        execution_snapshot={"engine_version": "test"},
    )
    rendered = RenderService().render(canonical)

    assert canonical.fields["title"].value == "接口目录维护说明"
    assert canonical.blocks[0].source_blocks == ["gen001_b001"]
    assert rendered.structured_json["data"]["title"] == "接口目录维护说明"
    assert rendered.structured_json["metadata"]["retrieved_at"] == (
        "2026-07-10T00:00:00Z"
    )
    assert rendered.structured_json["source_metadata"]["retrieved_at"] == (
        "2026-07-10T00:00:00Z"
    )
    assert "execution_snapshot" not in rendered.structured_json["metadata"]
    assert "execution_snapshot" not in rendered.structured_json["source_metadata"]
    assert canonical.doc_meta["execution_snapshot"] == {
        "engine_version": "test"
    }
    assert "# 接口目录维护说明" in rendered.markdown
    assert rendered.chunks
    assert all(chunk["text"] for chunk in rendered.chunks)
    assert all(chunk["source_block_ids"] for chunk in rendered.chunks)


def test_validation_service_checks_schema_and_render_outputs():
    from app.services.render_service import RenderedArtifacts
    from app.services.validation_service import ValidationService

    schema = __import__(
        "app.services.schema_service",
        fromlist=["SchemaService"],
    ).SchemaService(SCHEMAS_DIR).load_schema("policy_doc")
    rendered = RenderedArtifacts(
        structured_json={
            "task_id": "task_invalid",
            "doc_id": "doc_invalid",
            "schema_id": "policy_doc",
            "data": {"title": "缺字段"},
            "metadata": {},
            "blocks": [{"block_id": "blk_1", "text": "正文"}],
            "assets": [],
            "execution_snapshot": {},
        },
        markdown="# 缺字段\n",
        chunks=[{"chunk_id": "chunk_1", "text": "正文", "source_block_ids": ["missing"]}],
    )

    report = ValidationService().validate(
        task_id="task_invalid",
        schema=schema,
        rendered=rendered,
    )

    assert report.passed is False
    assert any(issue.field_id == "issuer" for issue in report.issues)
    assert any(issue.code == "chunk_source_missing" for issue in report.issues)


def test_package_service_writes_manifest_zip_and_verifier_passes(tmp_path):
    from app.services.canonical_service import CanonicalService
    from app.services.chunk_organizer_service import ChunkOrganizerService
    from app.services.package_service import PackageService
    from app.services.package_verifier_service import PackageVerifierService
    from app.services.render_service import RenderedArtifacts, RenderService
    from app.services.transform_service import TransformService
    from app.services.validation_service import ValidationService

    task_id = "task_contract_001"
    uir, schema, template, mapping_report = run_mapping(
        task_id,
        "contract/contract_001_standard.json",
        "contract_doc",
        "contract_doc_base_v1",
    )
    transform_result = TransformService().transform(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=mapping_report,
    )
    canonical = CanonicalService().build_canonical(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        transform_result=transform_result,
        mapping_report=mapping_report,
        execution_snapshot={"engine_version": "test"},
    )
    rendered = RenderService().render(canonical)
    preliminary_validation_report = ValidationService().validate(
        task_id=task_id,
        schema=schema,
        rendered=rendered,
    )
    organized_chunks, content_organization_report = ChunkOrganizerService().organize_chunks(
        chunks=rendered.chunks,
        canonical_model=canonical,
        schema=schema,
        mapping_report=mapping_report,
        validation_report=preliminary_validation_report,
        task_id=task_id,
        doc_id=uir.doc_id,
        schema_id=schema.schema_id,
        template_id=template.template_id,
        template_version=template.version,
    )
    rendered = RenderedArtifacts(
        structured_json=rendered.structured_json,
        markdown=rendered.markdown,
        chunks=organized_chunks,
    )
    validation_report = ValidationService().validate(
        task_id=task_id,
        schema=schema,
        rendered=rendered,
        require_content_organization=True,
    )

    package_result = PackageService(tmp_path).create_package(
        task_id=task_id,
        doc_id=uir.doc_id,
        schema=schema,
        template=template,
        canonical=canonical,
        rendered=rendered,
        mapping_report=mapping_report,
        transform_report=transform_result.report,
        validation_report=validation_report,
        content_organization_report=content_organization_report,
    )

    package_dir = Path(package_result.metadata.zip_path).parent
    assert (package_dir / "content.json").is_file()
    assert (package_dir / "content.md").is_file()
    assert (package_dir / "chunks.jsonl").is_file()
    assert (package_dir / "content_organization_report.json").is_file()
    assert (package_dir / "metadata.json").is_file()
    assert (package_dir / "manifest.json").is_file()
    assert Path(package_result.metadata.zip_path).is_file()
    assert package_result.metadata.sha256
    assert package_result.verifier_report.passed is True

    chunks = [
        json.loads(line)
        for line in (package_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert chunks
    assert all("summary" in chunk for chunk in chunks)
    assert all("keywords" in chunk for chunk in chunks)
    assert all("tags" in chunk for chunk in chunks)
    assert all("source_links" in chunk for chunk in chunks)

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest_files = {file["path"]: file for file in manifest["files"]}
    assert manifest["package_version"] == "1.0.0"
    assert manifest_files["content.json"]["role"] == "structured_json"
    assert manifest_files["metadata.json"]["role"] == "package_metadata"
    assert manifest_files["content_organization_report.json"]["role"] == (
        "content_organization_report"
    )
    assert manifest_files["verifier_report.json"]["role"] == "verifier_report"

    with zipfile.ZipFile(package_result.metadata.zip_path) as archive:
        assert {
            "content.json",
            "content.md",
            "chunks.jsonl",
            "content_organization_report.json",
            "metadata.json",
            "manifest.json",
        }.issubset(
            set(archive.namelist())
        )

    verifier_report = PackageVerifierService().verify_package(package_dir)
    assert verifier_report.passed is True
    strict_report = PackageVerifierService().verify_package(package_dir, strict=True)
    assert strict_report.passed is True


def test_package_verifier_strict_fails_bad_checksum(tmp_path):
    from app.services.package_verifier_service import PackageVerifierService

    package_dir = tmp_path / "bad_checksum"
    package_dir.mkdir()
    (package_dir / "content.json").write_text("{}", encoding="utf-8")
    (package_dir / "content.md").write_text("# ok\n", encoding="utf-8")
    (package_dir / "chunks.jsonl").write_text(
        json.dumps(
            {
                "chunk_id": "chunk_1",
                "text": "hello",
                "tags": {},
                "keywords": [],
                "summary": "",
                "source_block_ids": ["blk_1"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (package_dir / "mapping_report.json").write_text("{}", encoding="utf-8")
    (package_dir / "validation_report.json").write_text("{}", encoding="utf-8")
    (package_dir / "content_organization_report.json").write_text("{}", encoding="utf-8")
    (package_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "1.1",
                "package_id": "pkg_bad_checksum",
                "package_version": "1.0.0",
                "task_id": "task_bad_checksum",
                "doc_id": "doc_bad_checksum",
                "created_at": "2026-06-25T00:00:00+00:00",
                "files": [
                    {
                        "path": "content.json",
                        "required": True,
                        "media_type": "application/json",
                        "sha256": "not-a-real-checksum",
                        "bytes": 2,
                        "role": "structured_json",
                    }
                ],
                "generator": {"name": "test", "version": "0"},
            }
        ),
        encoding="utf-8",
    )

    report = PackageVerifierService().verify_package(package_dir, strict=True)

    assert report.passed is False
    assert any(error.code == "checksum_mismatch" for error in report.errors)


def test_package_verifier_strict_fails_invalid_jsonl(tmp_path):
    from app.services.package_verifier_service import PackageVerifierService

    package_dir = tmp_path / "invalid_jsonl"
    package_dir.mkdir()
    for name, payload in {
        "content.json": "{}",
        "mapping_report.json": "{}",
        "validation_report.json": "{}",
        "content_organization_report.json": "{}",
        "metadata.json": "{}",
    }.items():
        (package_dir / name).write_text(payload, encoding="utf-8")
    (package_dir / "content.md").write_text("# ok\n", encoding="utf-8")
    (package_dir / "chunks.jsonl").write_text("{invalid json}\n", encoding="utf-8")

    from app.services.manifest_service import ManifestService

    files = [path for path in package_dir.iterdir() if path.name != "manifest.json"]
    manifest = {
        "manifest_version": "1.1",
        "package_id": "pkg_invalid_jsonl",
        "package_version": "1.0.0",
        "task_id": "task_invalid_jsonl",
        "doc_id": "doc_invalid_jsonl",
        "created_at": "2026-06-25T00:00:00+00:00",
        "files": [
            {
                "path": path.name,
                "required": True,
                "media_type": ManifestService.media_type(path.name),
                "sha256": ManifestService.sha256_file(path),
                "bytes": path.stat().st_size,
                "role": ManifestService.role(path.name),
            }
            for path in files
        ],
        "generator": {"name": "test", "version": "0"},
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = PackageVerifierService().verify_package(package_dir, strict=True)

    assert report.passed is False
    assert any(error.code == "chunks_jsonl_invalid" for error in report.errors)


def test_package_verifier_fails_when_required_file_missing(tmp_path):
    from app.services.package_verifier_service import PackageVerifierService

    package_dir = tmp_path / "broken_package"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "1.1",
                "package_id": "pkg_broken",
                "package_version": "1.0.0",
                "task_id": "task_broken",
                "doc_id": "doc_broken",
                "created_at": "2026-06-25T00:00:00+00:00",
                "files": [
                    {
                        "path": "content.json",
                        "required": True,
                        "media_type": "application/json",
                        "sha256": "missing",
                        "bytes": 0,
                        "role": "structured_json",
                    }
                ],
                "generator": {"name": "test", "version": "0"},
            }
        ),
        encoding="utf-8",
    )

    report = PackageVerifierService().verify_package(package_dir)

    assert report.passed is False
    assert any(error.code == "required_file_missing" for error in report.errors)
