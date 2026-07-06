import json
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
SDK_ROOT = ROOT / "sdk" / "python"
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

from schemapack_client import SchemaPackClient  # noqa: E402


def test_client_calls_public_api_and_downloads_package(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/package/download"):
            return httpx.Response(200, content=b"PK-package")
        payloads = {
            "/api/v1/documents/import": {"doc_id": "doc_1", "status": "imported"},
            "/api/v1/external-uir/convert": {
                "standard_uir": {"doc_id": "doc_1"}
            },
            "/api/v1/tasks": {"task_id": "task_1", "status": "created"},
            "/api/v1/tasks/task_1/execute": {
                "task_id": "task_1",
                "status": "completed",
            },
            "/api/v1/schemas": {"items": [], "total": 0},
            "/api/v1/external-uir/adapters": {"items": [], "total": 0},
        }
        return httpx.Response(200, json=payloads[request.url.path])

    transport = httpx.MockTransport(handler)
    output = tmp_path / "package.zip"
    with SchemaPackClient(
        "https://schemapack.test",
        api_key="secret-test-key",
        transport=transport,
    ) as client:
        assert client.import_uir({"doc_id": "doc_1"})["doc_id"] == "doc_1"
        assert (
            client.convert_external_uir({"id": "external_1"})["standard_uir"][
                "doc_id"
            ]
            == "doc_1"
        )
        assert client.create_task("doc_1", "policy_doc", "policy_doc_base_v1")[
            "task_id"
        ] == "task_1"
        assert client.execute_task("task_1")["status"] == "completed"
        assert client.list_schemas()["total"] == 0
        assert client.list_adapters()["total"] == 0
        assert client.download_package("task_1", output) == output

    assert output.read_bytes() == b"PK-package"
    assert all(
        request.headers["X-API-Key"] == "secret-test-key"
        for request in requests
    )
    imported = json.loads(requests[0].content)
    assert imported == {"uir": {"doc_id": "doc_1"}}


def test_client_error_does_not_expose_api_key() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, json={"detail": "request failed"})
    )

    with (
        SchemaPackClient(
            "https://schemapack.test",
            api_key="secret-test-key",
            transport=transport,
        ) as client,
        pytest.raises(RuntimeError) as caught,
    ):
        client.list_schemas()

    assert "secret-test-key" not in str(caught.value)
