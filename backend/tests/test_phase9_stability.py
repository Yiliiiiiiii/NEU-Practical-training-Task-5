import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.v1.mappings import (
    get_candidate_service,
    get_mapping_service,
    get_review_service,
)
from app.api.v1.tasks import get_conversion_service, get_package_service
from app.config import Settings
from app.db.models import Base, Document
from app.main import create_app
from app.schemas.uir import UIRDocument
from app.services.storage_service import StorageService
from app.services.task_lock_service import TaskMutationConflict, TaskMutationRegistry


def test_same_task_mutation_is_rejected_while_lock_is_held():
    registry = TaskMutationRegistry()

    with registry.task_mutation("task_1"):
        with pytest.raises(TaskMutationConflict, match="task_1"):
            with registry.task_mutation("task_1"):
                pass

    with registry.task_mutation("task_1"):
        pass


def test_different_task_mutations_are_independent():
    registry = TaskMutationRegistry()

    with registry.task_mutation("task_1"):
        with registry.task_mutation("task_2"):
            assert registry.is_locked("task_1") is True
            assert registry.is_locked("task_2") is True

    assert registry.is_locked("task_1") is False
    assert registry.is_locked("task_2") is False


class _MustNotRunService:
    def __getattr__(self, name):
        raise AssertionError(f"service method must not run while task is locked: {name}")


@pytest.fixture()
def locked_api_client() -> Iterator[tuple[TestClient, TaskMutationRegistry]]:
    app = create_app(init_database=False)
    registry = TaskMutationRegistry()
    app.dependency_overrides[deps.get_task_mutation_registry] = lambda: registry
    for dependency in (
        get_candidate_service,
        get_mapping_service,
        get_review_service,
        get_conversion_service,
        get_package_service,
    ):
        app.dependency_overrides[dependency] = lambda: _MustNotRunService()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, registry


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/tasks/task_locked/generate-candidates", {}),
        ("/api/v1/tasks/task_locked/map", {}),
        ("/api/v1/tasks/task_locked/mappings/review", {"reviews": []}),
        ("/api/v1/tasks/task_locked/convert", {}),
        ("/api/v1/tasks/task_locked/package", {}),
    ],
)
def test_mutating_endpoints_return_deterministic_conflict_when_locked(
    locked_api_client,
    path,
    payload,
):
    client, registry = locked_api_client

    with registry.task_mutation("task_locked"):
        response = client.post(path, json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_ERROR"
    assert "already being modified" in response.json()["error"]["message"]


@pytest.mark.parametrize("operation", ["convert", "package"])
def test_overlapping_api_mutations_return_one_success_and_one_conflict(operation):
    app = create_app(init_database=False)
    registry = TaskMutationRegistry()
    entered = threading.Event()
    release = threading.Event()

    class BlockingService:
        @staticmethod
        def _block():
            entered.set()
            assert release.wait(timeout=5)

        def convert(self, **_kwargs):
            self._block()
            return "rendered", ["content.json", "content.md", "chunks.json"]

        def create_package(self, _task_id: str, _version: str):
            self._block()
            return {
                "package_id": "pkg_concurrent",
                "status": "completed",
                "zip_path": "packages/pkg_concurrent/standard_package.zip",
                "sha256": "abc",
            }

    service = BlockingService()
    app.dependency_overrides[deps.get_task_mutation_registry] = lambda: registry
    if operation == "convert":
        path = "/api/v1/tasks/task_concurrent/convert"
        app.dependency_overrides[get_conversion_service] = lambda: service
    else:
        path = "/api/v1/tasks/task_concurrent/package"
        app.dependency_overrides[get_package_service] = lambda: service

    with TestClient(app, raise_server_exceptions=False) as client:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(client.post, path, json={})
            assert entered.wait(timeout=5)
            second = client.post(path, json={})
            release.set()
            first = first_future.result(timeout=5)

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    conflict = first if first.status_code == 409 else second
    assert conflict.json()["error"]["code"] == "TASK_STATE_ERROR"


def test_concurrent_duplicate_document_import_keeps_one_valid_record(tmp_path):
    database_path = tmp_path / "concurrent.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    entered = threading.Event()
    release = threading.Event()

    class SlowFirstWriteStorage(StorageService):
        _guard = threading.Lock()
        _delayed = False

        def save_json(self, relative_path, data):
            with self._guard:
                should_delay = not self._delayed and str(relative_path).endswith("uir.json")
                if should_delay:
                    self._delayed = True
            if should_delay:
                entered.set()
                assert release.wait(timeout=5)
            return super().save_json(relative_path, data)

    storage = SlowFirstWriteStorage(tmp_path / "storage")
    app = create_app(
        Settings(storage_root=str(storage.root), database_url=f"sqlite:///{database_path}"),
        init_database=False,
    )

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_storage_service] = lambda: storage
    uir = {
        "uir_version": "1.0",
        "doc_id": "doc_concurrent",
        "metadata": {"title": "Concurrent document"},
        "blocks": [],
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(
                client.post,
                "/api/v1/documents/import",
                json={"uir": uir},
            )
            assert entered.wait(timeout=5)
            second = client.post("/api/v1/documents/import", json={"uir": uir})
            release.set()
            first = first_future.result(timeout=5)

    assert first.status_code == 200
    assert second.status_code == 200
    with session_factory() as db:
        assert db.query(Document).count() == 1
    stored = UIRDocument.model_validate(
        storage.read_json("documents/doc_concurrent/uir.json")
    )
    assert stored.doc_id == uir["doc_id"]
    assert stored.metadata == uir["metadata"]
    assert list(storage.resolve("documents/doc_concurrent").glob("*.tmp")) == []
