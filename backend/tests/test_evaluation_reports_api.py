from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    app = create_app(
        Settings(
            storage_root=str(tmp_path / "storage"),
            database_url=f"sqlite:///{tmp_path / 'unused.db'}",
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def test_knowledge_loop_report_returns_unavailable_when_missing(client: TestClient):
    response = client.get("/api/v1/evaluation-reports/real-world-knowledge-loop")

    assert response.status_code == 200
    assert response.json()["status"] in {"available", "unavailable"}


def test_unknown_evaluation_report_is_rejected(client: TestClient):
    response = client.get("/api/v1/evaluation-reports/not-allowed")

    assert response.status_code == 404
