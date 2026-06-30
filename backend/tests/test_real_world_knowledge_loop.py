import importlib.util
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
PRODUCTION_UIR = ROOT / "examples" / "production_like" / "uir" / "policy"


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


@pytest.fixture
def knowledge_client(tmp_path: Path) -> Iterator[TestClient]:
    from app.api.deps import get_db, get_storage_service
    from app.services.storage_service import StorageService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    storage_root = tmp_path / "storage"
    app = create_app(Settings(storage_root=str(storage_root), database_url="sqlite:///unused.db"))

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage_service] = lambda: StorageService(storage_root)

    with TestClient(app) as client:
        yield client


def import_policy_document(client: TestClient) -> str:
    uir = json.loads(
        (PRODUCTION_UIR / "policy_002_alias_variants.json").read_text(encoding="utf-8")
    )
    response = client.post("/api/v1/documents/import", json={"uir": uir})
    assert response.status_code == 200
    return response.json()["doc_id"]


def create_policy_task(
    client: TestClient,
    doc_id: str,
    options: dict | None = None,
) -> str:
    response = client.post(
        "/api/v1/tasks",
        json={
            "doc_id": doc_id,
            "schema_id": "policy_doc",
            "template_id": "policy_doc_base_v1",
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False, **(options or {})},
        },
    )
    assert response.status_code == 200
    return response.json()["task_id"]


def execute_task(client: TestClient, task_id: str) -> dict:
    response = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert response.status_code == 200
    return response.json()


def approve_title_review(client: TestClient, task_id: str | None = None) -> dict:
    reviews = client.get("/api/v1/reviews", params={"status": "pending"}).json()["items"]
    title_review = next(
        item
        for item in reviews
        if item["target_field_id"] == "title"
        and (task_id is None or item["task_id"] == task_id)
    )
    response = client.post(
        f"/api/v1/reviews/{title_review['review_id']}/approve",
        json={
            "reviewer": "topic5_eval",
            "comment": "approve alias",
            "create_knowledge_candidate": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_draft_pack_does_not_affect_effective_template(knowledge_client: TestClient) -> None:
    doc_id = import_policy_document(knowledge_client)
    task_id = create_policy_task(knowledge_client, doc_id)
    execute_task(knowledge_client, task_id)
    before = knowledge_client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "policy_doc", "template_id": "policy_doc_base_v1"},
    ).json()
    approve_title_review(knowledge_client, task_id)
    candidate = knowledge_client.get("/api/v1/knowledge/candidates").json()["items"][0]
    accepted = knowledge_client.post(
        f"/api/v1/knowledge/candidates/{candidate['candidate_id']}/accept"
    )
    assert accepted.status_code == 200
    pack = knowledge_client.post(
        "/api/v1/knowledge/packs",
        json={
            "schema_id": "policy_doc",
            "template_id": "policy_doc_base_v1",
            "name": "topic5 policy aliases",
            "created_by": "topic5_eval",
        },
    ).json()
    draft = knowledge_client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "policy_doc", "template_id": "policy_doc_base_v1"},
    ).json()
    assert draft == before
    active = knowledge_client.post(f"/api/v1/knowledge/packs/{pack['pack_id']}/activate")
    assert active.status_code == 200
    after = knowledge_client.get(
        "/api/v1/knowledge/effective-template",
        params={"schema_id": "policy_doc", "template_id": "policy_doc_base_v1"},
    ).json()
    assert after != before


def test_badcase_candidate_is_blocked(knowledge_client: TestClient) -> None:
    doc_id = import_policy_document(knowledge_client)
    probe_task_id = create_policy_task(knowledge_client, doc_id)
    execute_task(knowledge_client, probe_task_id)
    reviews = knowledge_client.get("/api/v1/reviews", params={"status": "pending"}).json()["items"]
    source_field = next(item for item in reviews if item["target_field_id"] == "title")[
        "source_field_name"
    ]

    blocked_task_id = create_policy_task(
        knowledge_client,
        doc_id,
        options={
            "badcases": [
                {
                    "source_field": source_field,
                    "forbidden_target_fields": ["title"],
                }
            ]
        },
    )
    execute_task(knowledge_client, blocked_task_id)
    approve_title_review(knowledge_client, blocked_task_id)
    candidates = knowledge_client.get("/api/v1/knowledge/candidates").json()["items"]
    candidate = next(item for item in candidates if item["status"] == "blocked")
    assert candidate["badcase_hit"] is True
    accept = knowledge_client.post(
        f"/api/v1/knowledge/candidates/{candidate['candidate_id']}/accept"
    )
    assert accept.status_code == 400

def test_knowledge_loop_report_sections() -> None:
    evaluator = load_script("eval_knowledge_loop_real_world")
    report = evaluator.build_report(
        {
            "before": {"aliases": {"title": ["title"]}},
            "draft_effective": {"aliases": {"title": ["title"]}},
            "active_effective": {"aliases": {"title": ["title", "通知名称"]}},
            "approved_reviews": [{"review_id": "r1"}],
            "accepted_candidates": [{"candidate_id": "c1"}],
            "blocked_candidates": [{"candidate_id": "blocked"}],
            "metrics": {"active_packs": 1},
            "before_mapping": {"mappings": []},
            "old_mapping_after_activation": {"mappings": []},
            "before_recall": 0.5,
            "after_recall": 1.0,
            "required_coverage_before": 0.5,
            "required_coverage_after": 1.0,
        }
    )
    markdown = evaluator.render_markdown(report)

    assert report["summary"]["old_snapshot_unchanged"] is True
    assert report["summary"]["badcase_violation_count"] == 0
    assert report["summary"]["blocked_candidate_count"] == 1
    assert "## Before/After Recall" in markdown
    assert "## Required Coverage" in markdown
    assert "## Review Approvals" in markdown
    assert "## Candidate Acceptance" in markdown
    assert "## Pack Activation" in markdown
    assert "## Snapshot Invariant" in markdown
