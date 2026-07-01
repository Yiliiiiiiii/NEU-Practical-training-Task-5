import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_full_package(tmp_path: Path, *, linked: bool = True) -> Path:
    package = tmp_path / "package"
    package.mkdir(parents=True)
    metadata = {
        "package_id": "pkg_1",
        "task_id": "task_1",
        "doc_id": "doc_1",
        "schema_id": "policy_doc",
        "schema_version": "1.0.0",
        "template_id": "policy_doc_base_v1",
        "template_version": "1.0.0",
    }
    artifacts: dict[str, Any] = {
        "metadata.json": metadata,
        "content.json": {"title": "示例政策", "year": 2026, "body": {"scope": "企业"}},
        "canonical.json": {"fields": {"title": "示例政策"}},
        "mapping_report.json": {"summary": {"mapped_count": 1}},
        "validation_report.json": {"passed": True},
        "content_organization_report.json": {"chunk_count": 2},
        "verifier_report.json": {"passed": True},
    }
    for name, value in artifacts.items():
        (package / name).write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8"
        )
    (package / "content.md").write_text("# 示例政策\n正文", encoding="utf-8")
    chunks = [
        {
            "chunk_id": "parent",
            "text": "父级正文",
            "granularity": "parent",
            "title_path": ["示例政策"],
            "summary": "父级摘要",
            "keywords": ["政策"],
            "tags": {
                "content": ["policy"],
                "management": ["official_source"],
                "quality": ["source_linked"],
            },
            "source_block_ids": ["b1"] if linked else [],
            "source_links": [],
        },
        {
            "chunk_id": "child",
            "text": "子级正文",
            "granularity": "child",
            "parent_chunk_id": "parent",
            "title_path": ["示例政策", "范围"],
            "summary": "子级摘要",
            "keywords": ["范围"],
            "tags": {"content": ["scope"], "management": [], "quality": []},
            "source_block_ids": ["b2"] if linked else [],
            "source_links": [],
        },
    ]
    (package / "chunks.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in chunks) + "\n",
        encoding="utf-8",
    )
    files = []
    for path in sorted(package.iterdir()):
        files.append(
            {
                "path": path.name,
                "required": True,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "manifest_version": "1.1",
        "package_id": "pkg_1",
        "task_id": "task_1",
        "doc_id": "doc_1",
        "files": files,
        "generator": {
            "schema_id": "policy_doc",
            "schema_version": "1.0.0",
            "template_id": "policy_doc_base_v1",
            "template_version": "1.0.0",
        },
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return package


def zip_package(package: Path, target: Path) -> Path:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package.iterdir():
            archive.write(path, path.name)
    return target


def test_structured_csv_exports_directory_and_zip(tmp_path: Path) -> None:
    module = load_script("export_structured_csv")
    package = write_full_package(tmp_path)
    archive = zip_package(package, tmp_path / "package.zip")
    directory_result = module.export_structured_csv(package, tmp_path / "dir.csv")
    zip_result = module.export_structured_csv(archive, tmp_path / "zip.csv")
    assert directory_result["row_count"] >= 3
    assert zip_result["row_count"] == directory_result["row_count"]
    assert "schema_id" in (tmp_path / "dir.csv").read_text(encoding="utf-8-sig")


def test_rag_export_filters_granularity_and_options(tmp_path: Path) -> None:
    module = load_script("export_rag_corpus")
    package = write_full_package(tmp_path)
    result = module.export_rag_corpus(
        package,
        tmp_path / "rag.jsonl",
        granularity="child",
        include_summary=False,
        include_keywords=False,
    )
    rows = [
        json.loads(line)
        for line in (tmp_path / "rag.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert result["row_count"] == 1
    assert rows[0]["id"] == "child"
    assert rows[0]["metadata"]["granularity"] == "child"
    assert "summary" not in rows[0]["metadata"]
    assert "keywords" not in rows[0]["metadata"]


def test_rag_export_warns_or_fails_for_missing_source_links(tmp_path: Path) -> None:
    module = load_script("export_rag_corpus")
    package = write_full_package(tmp_path, linked=False)
    warning = module.export_rag_corpus(package, tmp_path / "warning.jsonl")
    assert warning["missing_source_link_count"] == 2
    try:
        module.export_rag_corpus(
            package,
            tmp_path / "failed.jsonl",
            fail_on_missing_source_links=True,
        )
    except ValueError as exc:
        assert "source" in str(exc).lower()
    else:
        raise AssertionError("strict source-link mode must fail")
