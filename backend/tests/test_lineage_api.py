# ruff: noqa: F401, F811

from tests.test_task_execution_api import (
    create_policy_task,
    execution_client,
    import_policy_document,
)


def executed_task(client) -> str:
    doc_id = import_policy_document(client, "policy_001_standard.json")
    task_id = create_policy_task(client, doc_id)
    response = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert response.status_code == 200
    return task_id


def test_get_task_lineage_returns_graph(execution_client) -> None:
    client, _storage_root = execution_client
    task_id = executed_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}/lineage")

    assert response.status_code == 200
    assert response.json()["task_id"] == task_id
    assert response.json()["nodes"]


def test_get_lineage_summary_returns_counts(execution_client) -> None:
    client, _storage_root = execution_client
    task_id = executed_task(client)

    response = client.get(f"/api/v1/tasks/{task_id}/lineage/summary")

    assert response.status_code == 200
    assert response.json()["node_count"] > 0
    assert response.json()["artifact_lineage_coverage"] == 1.0


def test_get_field_lineage_returns_subgraph(execution_client) -> None:
    client, _storage_root = execution_client
    task_id = executed_task(client)

    response = client.get(
        f"/api/v1/tasks/{task_id}/lineage/fields/title",
        params={"direction": "upstream", "max_depth": 8},
    )

    assert response.status_code == 200
    assert response.json()["root_node_id"] == "lineage:canonical_field:title"
    assert response.json()["edges"]


def test_get_chunk_lineage_returns_subgraph(execution_client) -> None:
    client, _storage_root = execution_client
    task_id = executed_task(client)
    chunks = client.get(f"/api/v1/tasks/{task_id}/reports/chunks").json()["items"]

    response = client.get(
        f"/api/v1/tasks/{task_id}/lineage/chunks/{chunks[0]['chunk_id']}"
    )

    assert response.status_code == 200
    assert response.json()["root_node_id"].startswith("lineage:chunk:")


def test_get_artifact_lineage_returns_manifest_and_contract(execution_client) -> None:
    client, _storage_root = execution_client
    task_id = executed_task(client)

    response = client.get(
        f"/api/v1/tasks/{task_id}/lineage/artifacts/content.json"
    )

    assert response.status_code == 200
    node_types = {node["node_type"] for node in response.json()["nodes"]}
    assert "package_manifest_entry" in node_types
    assert "consumer_contract" in node_types


def test_unknown_task_returns_404(execution_client) -> None:
    client, _storage_root = execution_client

    response = client.get("/api/v1/tasks/task_missing/lineage")

    assert response.status_code == 404


def test_unknown_field_returns_404_consistently(execution_client) -> None:
    client, _storage_root = execution_client
    task_id = executed_task(client)

    response = client.get(
        f"/api/v1/tasks/{task_id}/lineage/fields/not_a_field"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "lineage root not found"


def test_lineage_api_does_not_expose_secrets(execution_client) -> None:
    client, _storage_root = execution_client
    doc_id = import_policy_document(client, "policy_001_standard.json")
    secret = "sk-lineage-api-secret"
    task_id = create_policy_task(
        client,
        doc_id,
        options={"api_key": secret, "note": f"Bearer {secret}"},
    )
    assert client.post(f"/api/v1/tasks/{task_id}/execute").status_code == 200

    serialized = client.get(f"/api/v1/tasks/{task_id}/lineage").text.lower()

    assert secret not in serialized
    assert '"api_key"' not in serialized
