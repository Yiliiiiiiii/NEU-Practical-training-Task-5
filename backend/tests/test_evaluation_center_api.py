from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def evaluation_client(tmp_path) -> Iterator[TestClient]:
    from app.api.deps import get_settings, get_storage_service
    from app.api.v1.evaluation_center import get_evaluation_center_service
    from app.services.evaluation_center_service import EvaluationCenterService
    from app.services.storage_service import StorageService

    reports_root = tmp_path / "reports"
    reports_root.mkdir()
    (reports_root / "phase_5.json").write_text(
        '{"adapter_trace_coverage": 1.0}',
        encoding="utf-8",
    )
    settings = Settings(
        storage_root=str(tmp_path / "storage"),
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
    )
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_storage_service] = lambda: StorageService(
        tmp_path / "storage"
    )
    app.dependency_overrides[get_evaluation_center_service] = lambda: (
        EvaluationCenterService(
            StorageService(tmp_path / "storage"),
            reports_root=reports_root,
        )
    )
    with TestClient(app) as client:
        yield client


def test_evaluation_center_registry_run_and_scorecard(evaluation_client) -> None:
    datasets = evaluation_client.get("/api/v1/evaluation-center/datasets")
    assert datasets.status_code == 200
    assert datasets.json()["items"]

    metrics = evaluation_client.get("/api/v1/evaluation-center/metrics")
    assert metrics.status_code == 200
    assert any(
        item["metric_id"] == "badcase_violation_count"
        for item in metrics.json()["items"]
    )

    created = evaluation_client.post(
        "/api/v1/evaluation-center/run",
        json={
            "dataset_id": "real_world_uir_2026_07_03",
            "eval_type": "phase_5_smoke",
            "git_commit": "test",
            "metrics": {
                "adapter_trace_coverage": 1.0,
                "badcase_violation_count": 0,
                "llm_auto_accepted_count": 0,
                "package_verification_rate": 1.0,
            },
            "report_paths": {"json": "reports/adapter_framework_eval_report.json"},
        },
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    assert created.json()["passed"] is True

    assert evaluation_client.get("/api/v1/evaluation-center/runs").json()["total"] == 1
    assert (
        evaluation_client.get(f"/api/v1/evaluation-center/runs/{run_id}").status_code
        == 200
    )
    scorecard = evaluation_client.get("/api/v1/evaluation-center/scorecard")
    assert scorecard.status_code == 200
    assert scorecard.json()["passed"] is True
    assert scorecard.json()["summary"]["status"] == "passed"
    assert scorecard.json()["cards"]
    assert scorecard.json()["warnings"]


def test_registered_report_can_be_opened(evaluation_client) -> None:
    created = evaluation_client.post(
        "/api/v1/evaluation-center/run",
        json={
            "dataset_id": "external_uir_adapter_v1",
            "eval_type": "adapter",
            "git_commit": "test",
            "metrics": {"adapter_trace_coverage": 1.0},
            "report_paths": {"json": "reports/phase_5.json"},
        },
    )
    run_id = created.json()["run_id"]

    report = evaluation_client.get(
        f"/api/v1/evaluation-center/runs/{run_id}/reports/json"
    )

    assert report.status_code == 200
    assert report.json() == {"adapter_trace_coverage": 1.0}
