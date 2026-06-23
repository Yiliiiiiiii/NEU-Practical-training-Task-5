import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.db.models import (
    Base,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.main import create_app
from app.schemas.api import TaskReplayRequest
from app.services.package_service import PackageService
from app.services.storage_service import StorageService
from app.services.task_service import TaskService


@pytest.fixture()
def replay_context(tmp_path) -> Iterator[tuple[Session, StorageService]]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    storage = StorageService(tmp_path / "storage")
    with factory() as db:
        yield db, storage


@pytest.fixture()
def replay_client(replay_context) -> Iterator[TestClient]:
    db, storage = replay_context
    app = create_app(init_database=False)

    def override_db():
        yield db

    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_storage_service] = lambda: storage
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed_parent(db: Session, *, with_mapping: bool = True) -> str:
    schema = {
        "schema_id": "schema_replay",
        "name": "Replay Schema",
        "version": "1.0.0",
        "fields": [
            {
                "field_id": "title",
                "name": "title",
                "display_name": "Title",
                "type": "string",
                "required": True,
            }
        ],
        "json_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        },
    }
    template = {
        "template_id": "template_replay",
        "schema_id": "schema_replay",
        "name": "Replay Template",
        "version": "1.0.0",
        "aliases": {"title": ["doc_title"]},
    }
    db.add(Document(
        doc_id="doc_replay",
        title="Replay Source",
        uir_version="1.0",
        storage_path="documents/doc_replay/uir.json",
        block_count=0,
    ))
    db.add(TargetSchemaRecord(
        schema_id="schema_replay",
        name=schema["name"],
        version=schema["version"],
        schema_json=json.dumps(schema),
        json_schema=json.dumps(schema["json_schema"]),
    ))
    db.add(MappingTemplateRecord(
        template_id="template_replay",
        schema_id="schema_replay",
        name=template["name"],
        version=template["version"],
        template_json=json.dumps(template),
    ))
    db.add(ConversionTask(
        task_id="task_parent",
        parent_task_id=None,
        doc_id="doc_replay",
        schema_id="schema_replay",
        schema_version="1.0.0",
        template_id="template_replay",
        template_version="1.0.0",
        status="completed",
        input_hash="sha256:parent",
        options_json=json.dumps({"enable_llm_fallback": True, "chunk_size": 128}),
    ))
    db.add(FieldCandidateRecord(
        candidate_id="cand_parent_title",
        task_id="task_parent",
        doc_id="doc_replay",
        source_path="metadata.doc_title",
        source_name="doc_title",
        display_name="Document Title",
        value_sample=json.dumps("Replay Source"),
        inferred_type="string",
        source_blocks_json="[]",
        confidence=0.95,
    ))
    if with_mapping:
        db.add(FieldMappingRecord(
            mapping_id="map_parent_title",
            task_id="task_parent",
            candidate_id="cand_parent_title",
            target_field_id="title",
            method="alias_match",
            confidence=0.95,
            status="confirmed",
            need_review=False,
            evidence_json=json.dumps(["source_name matched aliases"]),
        ))
    db.commit()
    return "task_parent"


def test_task_service_replay_copies_confirmed_mappings_with_new_ids(replay_context):
    db, storage = replay_context
    parent_task_id = _seed_parent(db)

    child, counts = TaskService(db, storage).replay_task(
        parent_task_id,
        TaskReplayRequest(),
    )

    assert child.parent_task_id == parent_task_id
    assert child.task_id != parent_task_id
    assert child.status == "mapping_completed"
    assert counts == {"candidates": 1, "mappings": 1}
    assert json.loads(child.options_json)["enable_llm_fallback"] is False
    assert json.loads(child.options_json)["replay"]["repeat_model_calls"] is False

    child_candidates = db.query(FieldCandidateRecord).filter_by(task_id=child.task_id).all()
    child_mappings = db.query(FieldMappingRecord).filter_by(task_id=child.task_id).all()
    assert [candidate.candidate_id for candidate in child_candidates] != [
        "cand_parent_title"
    ]
    assert [mapping.mapping_id for mapping in child_mappings] != ["map_parent_title"]
    assert child_mappings[0].candidate_id == child_candidates[0].candidate_id
    assert child_mappings[0].target_field_id == "title"


def test_task_replay_api_returns_child_counts(replay_client, replay_context):
    db, _storage = replay_context
    parent_task_id = _seed_parent(db)

    response = replay_client.post(f"/api/v1/tasks/{parent_task_id}/replay", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["parent_task_id"] == parent_task_id
    assert body["child_task_id"].startswith("task_")
    assert body["status"] == "mapping_completed"
    assert body["copied_candidates"] == 1
    assert body["copied_mappings"] == 1
    assert body["repeat_model_calls"] is False


def test_replay_rejects_parent_without_confirmed_mappings(replay_context):
    db, storage = replay_context
    parent_task_id = _seed_parent(db, with_mapping=False)

    with pytest.raises(ValueError, match="no confirmed mappings"):
        TaskService(db, storage).replay_task(parent_task_id, TaskReplayRequest())


def test_config_snapshot_contains_replay_lineage_and_model_audit(replay_context):
    db, storage = replay_context
    parent_task_id = _seed_parent(db)
    child, _counts = TaskService(db, storage).replay_task(
        parent_task_id,
        TaskReplayRequest(),
    )
    storage.save_json(
        f"tasks/{child.task_id}/mapping_report.json",
        {
            "summary": {
                "llm_enabled": True,
                "llm_mode": "openai_compatible",
                "llm_model": "schema-map-model",
                "llm_prompt_version": "prompt-v10",
                "llm_status": "success",
                "llm_suggestion_count": 2,
                "llm_latency_ms": 321,
            }
        },
    )

    PackageService(db, storage)._generate_config_snapshot(child)

    snapshot = storage.read_json(f"tasks/{child.task_id}/config_snapshot.json")
    assert snapshot["snapshot_version"] == "1.1"
    assert snapshot["task_id"] == child.task_id
    assert snapshot["parent_task_id"] == parent_task_id
    assert snapshot["schema_ref"] == {"schema_id": "schema_replay", "version": "1.0.0"}
    assert snapshot["template_ref"] == {
        "template_id": "template_replay",
        "version": "1.0.0",
    }
    assert snapshot["confirmed_mapping_ids"]
    assert snapshot["model"]["mode"] == "openai_compatible"
    assert snapshot["model"]["status"] == "success"
    assert snapshot["prompt_version"] == "prompt-v10"
    assert db.get(ConversionTask, child.task_id).config_snapshot_path == (
        f"tasks/{child.task_id}/config_snapshot.json"
    )
