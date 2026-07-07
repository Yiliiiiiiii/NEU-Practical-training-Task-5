import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"


def load_script(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_inventory_flags_documents_with_fewer_than_two_retrieval_queries(
    tmp_path: Path,
) -> None:
    module = load_script("build_real_world_dataset_inventory")
    common = load_script("real_world_uir_common")
    dataset_dir = tmp_path / "real_world"
    (dataset_dir / "sources").mkdir(parents=True)
    (dataset_dir / "uir" / "policy").mkdir(parents=True)
    (dataset_dir / "gold").mkdir(parents=True)
    (dataset_dir / "sources" / "source_manifest.json").write_text(
        json.dumps({"items": [{"source_id": "doc-1"}]}),
        encoding="utf-8",
    )
    (dataset_dir / "uir" / "policy" / "doc-1.json").write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "metadata": {"doc_type": "policy_doc"},
                "blocks": [{"block_id": "doc-1_b001", "text": "content"}],
            }
        ),
        encoding="utf-8",
    )
    (dataset_dir / "gold" / "mapping_gold.jsonl").write_text(
        json.dumps({"doc_id": "doc-1"}) + "\n",
        encoding="utf-8",
    )
    (dataset_dir / "gold" / "real_world_badcases.jsonl").write_text(
        "",
        encoding="utf-8",
    )
    (dataset_dir / "gold" / "retrieval_queries.jsonl").write_text(
        json.dumps(
            {
                "query_id": "query-1",
                "doc_id": "doc-1",
                "relevant_source_block_ids": ["doc-1_b001"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    inventory = module.build_inventory(common.dataset_paths(dataset_dir))

    assert inventory["summary"]["missing_retrieval_queries"] == 0
    assert inventory["summary"]["insufficient_retrieval_queries"] == 1
    assert any(
        item["code"] == "insufficient_retrieval_queries"
        and "doc-1 has 1 retrieval query" in item["message"]
        for item in inventory["issues"]
    )


def test_inventory_excludes_queries_without_traceable_block_references(
    tmp_path: Path,
) -> None:
    module = load_script("build_real_world_dataset_inventory")
    common = load_script("real_world_uir_common")
    dataset_dir = tmp_path / "real_world"
    (dataset_dir / "sources").mkdir(parents=True)
    (dataset_dir / "uir" / "policy").mkdir(parents=True)
    (dataset_dir / "gold").mkdir(parents=True)
    (dataset_dir / "sources" / "source_manifest.json").write_text(
        json.dumps({"items": [{"source_id": "doc-1"}]}),
        encoding="utf-8",
    )
    (dataset_dir / "uir" / "policy" / "doc-1.json").write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "metadata": {"doc_type": "policy_doc"},
                "blocks": [{"block_id": "doc-1_b001", "text": "content"}],
            }
        ),
        encoding="utf-8",
    )
    (dataset_dir / "gold" / "mapping_gold.jsonl").write_text(
        json.dumps({"doc_id": "doc-1"}) + "\n",
        encoding="utf-8",
    )
    (dataset_dir / "gold" / "real_world_badcases.jsonl").write_text(
        "",
        encoding="utf-8",
    )
    invalid_queries = [
        {"query_id": "missing", "doc_id": "doc-1"},
        {
            "query_id": "wrong-type",
            "doc_id": "doc-1",
            "relevant_source_block_ids": "doc-1_b001",
        },
        {
            "query_id": "empty",
            "doc_id": "doc-1",
            "relevant_source_block_ids": [],
        },
    ]
    (dataset_dir / "gold" / "retrieval_queries.jsonl").write_text(
        "\n".join(json.dumps(row) for row in invalid_queries) + "\n",
        encoding="utf-8",
    )

    inventory = module.build_inventory(common.dataset_paths(dataset_dir))

    assert inventory["summary"]["retrieval_query_count"] == 3
    assert inventory["summary"]["valid_retrieval_query_count"] == 0
    assert inventory["summary"]["invalid_query_references"] == 3
    assert inventory["summary"]["missing_retrieval_queries"] == 1
    assert inventory["summary"]["insufficient_retrieval_queries"] == 1
    assert sum(
        item["code"] == "invalid_query_references"
        for item in inventory["issues"]
    ) == 3


def test_inventory_requires_gold_and_queries_for_every_uir() -> None:
    module = load_script("build_real_world_dataset_inventory")
    common = load_script("real_world_uir_common")

    inventory = module.build_inventory(
        common.dataset_paths(ROOT / "examples" / "real_world")
    )
    summary = inventory["summary"]

    assert summary["uir_count"] >= 30
    assert summary["valid_retrieval_query_count"] == summary["retrieval_query_count"]
    assert summary["invalid_query_references"] == 0
    assert summary["missing_mapping_gold"] == 0
    assert summary["missing_retrieval_queries"] == 0
    assert summary["insufficient_retrieval_queries"] == 0
    assert summary["orphan_manifest_items"] == 0
    assert summary["orphan_mapping_gold"] == 0
    assert summary["orphan_retrieval_queries"] == 0
    assert summary["invalid_block_references"] == 0
    assert summary["duplicate_ids"] == 0
    assert inventory["issues"] == []


def test_inventory_reports_doc_type_distribution_and_field_density() -> None:
    module = load_script("build_real_world_dataset_inventory")
    common = load_script("real_world_uir_common")

    inventory = module.build_inventory(
        common.dataset_paths(ROOT / "examples" / "real_world")
    )

    assert inventory["by_doc_type"] == {
        "general_doc": 15,
        "meeting_doc": 15,
        "policy_doc": 20,
        "procurement_doc": 10,
    }
    for doc_type, density in inventory["field_density"].items():
        assert density["documents"] == inventory["by_doc_type"][doc_type]
        assert density["avg_expected_mappings"] >= 3
        assert density["avg_retrieval_queries"] >= 2


def test_inventory_cross_references_badcases_and_source_blocks() -> None:
    module = load_script("build_real_world_dataset_inventory")
    common = load_script("real_world_uir_common")

    inventory = module.build_inventory(
        common.dataset_paths(ROOT / "examples" / "real_world")
    )
    summary = inventory["summary"]

    assert summary["badcase_count"] >= len(inventory["by_doc_type"])
    assert summary["invalid_badcase_references"] == 0
    assert summary["invalid_source_path_references"] == 0
    assert set(inventory["badcases_by_doc_type"]) == set(inventory["by_doc_type"])
