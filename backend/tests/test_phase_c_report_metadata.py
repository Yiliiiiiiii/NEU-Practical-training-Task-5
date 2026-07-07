import importlib.util
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_metadata_contains_phase_c_provenance() -> None:
    module = load_script("phase_c_report_metadata")

    metadata = module.build_run_metadata(
        packages_root="reports/real_world_packages",
        gold_path="examples/real_world/gold/mapping_gold.jsonl",
        badcases_path="examples/real_world/gold/real_world_badcases.jsonl",
        dataset_size=35,
    )

    assert metadata["run_id"].startswith("phase_c_")
    assert metadata["report_version"] == "phase_c_v1"
    assert metadata["packages_root"] == "reports/real_world_packages"
    assert metadata["gold_path"] == "examples/real_world/gold/mapping_gold.jsonl"
    assert metadata["badcases_path"] == "examples/real_world/gold/real_world_badcases.jsonl"
    assert metadata["dataset_size"] == 35
    assert metadata["git_branch"]
    assert metadata["git_commit"]


def test_strict_validation_report_includes_run_metadata(tmp_path: Path) -> None:
    module = load_script("analyze_strict_validation_failures")
    packages = tmp_path / "packages"
    packages.mkdir()
    with ZipFile(packages / "policy.zip", "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "metadata.json",
            json.dumps({"doc_id": "policy-1", "schema_id": "policy_doc"}),
        )
        archive.writestr(
            "validation_report.json",
            json.dumps({"passed": True, "issues": []}),
        )
        archive.writestr("mapping_report.json", json.dumps({"review_required_items": []}))
        archive.writestr("transform_report.json", json.dumps({"issues": []}))

    report = module.run(
        packages_root=packages,
        gold_path=None,
        out_path=tmp_path / "analysis.json",
        markdown_path=tmp_path / "analysis.md",
    )

    assert report["run_metadata"]["report_version"] == "phase_c_v1"
    assert report["run_metadata"]["dataset_size"] == 1
