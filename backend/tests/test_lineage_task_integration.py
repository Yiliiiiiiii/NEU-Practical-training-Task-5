# ruff: noqa: F401, F811

import json
from pathlib import Path

from app.services.lineage_graph_service import LineageGraphService
from tests.test_task_execution_api import (
    create_policy_task,
    execution_client,
    import_policy_document,
)


def test_task_execution_writes_lineage_reports_by_default(execution_client) -> None:
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id)

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 200
    report_paths = response.json()["report_paths"]
    assert Path(report_paths["lineage_graph"]).is_file()
    assert Path(report_paths["lineage_summary"]).is_file()
    graph = client.get(f"/api/v1/tasks/{task_id}/reports/lineage").json()
    summary = client.get(f"/api/v1/tasks/{task_id}/reports/lineage-summary").json()
    assert graph["task_id"] == task_id
    assert graph["nodes"]
    assert summary["node_count"] == len(graph["nodes"])
    assert summary["source_mode"] == "standard_uir"


def test_task_execution_can_disable_lineage(execution_client) -> None:
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id, options={"enable_lineage": False})

    response = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert response.status_code == 200
    assert "lineage_graph" not in response.json()["report_paths"]
    assert client.get(f"/api/v1/tasks/{task_id}/reports/lineage").status_code == 404


def test_non_strict_lineage_failure_keeps_successful_task(
    execution_client,
    monkeypatch,
) -> None:
    client, storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id, options={"strict_lineage": False})

    def fail_lineage(*args, **kwargs):
        raise RuntimeError("synthetic lineage failure")

    monkeypatch.setattr(LineageGraphService, "build", fail_lineage)
    response = client.post(f"/api/v1/tasks/{task_id}/execute")
    snapshot = json.loads(
        (storage_root / "tasks" / task_id / "execution_snapshot.json").read_text(
            encoding="utf-8"
        )
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert snapshot["lineage_warnings"] == ["synthetic lineage failure"]


def test_external_create_task_preserves_adapter_report(execution_client) -> None:
    client, _storage_root = execution_client
    payload = {
        "id": "external-lineage-1",
        "title": "External lineage",
        "chunks": [{"id": "b1", "type": "paragraph", "text": "正文"}],
    }
    imported = client.post(
        "/api/v1/external-uir/import",
        json={
            "payload": payload,
            "source_system": "lineage-test",
            "route_schema": True,
            "allow_llm": False,
        },
    )
    assert imported.status_code == 200
    imported_payload = imported.json()

    created = client.post(
        "/api/v1/external-uir/create-task",
        json={
            "doc_id": imported_payload["doc_id"],
            "schema_id": "general_doc",
            "template_id": "general_doc_base_v1",
            "route_report": imported_payload["route_report"],
            "adapter_report": imported_payload["adapter_report"],
        },
    )

    assert created.status_code == 200
    detail = client.get(f"/api/v1/tasks/{created.json()['task_id']}").json()
    adapter_report = detail["options"]["external_uir"]["adapter_report"]
    assert adapter_report["adapter_id"] == "block_list"
    assert adapter_report["trace_items"]
