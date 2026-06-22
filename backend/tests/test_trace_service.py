import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, TransformTraceRecord
from app.services.storage_service import StorageService
from app.services.trace_service import TraceService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    with TestSession() as session:
        yield session


@pytest.fixture()
def trace_service(db_session, tmp_path):
    storage = StorageService(tmp_path / "storage")
    return TraceService(db_session, storage)


def test_record_event_persists_trace(trace_service, db_session):
    trace_service.record_event(
        task_id="task_1",
        stage="field_transform",
        action="rename",
        target_field_id="title",
        before={"value": "old"},
        after={"value": "new"},
        reason="renamed",
    )
    db_session.commit()

    records = db_session.query(TransformTraceRecord).filter(
        TransformTraceRecord.task_id == "task_1"
    ).all()
    assert len(records) == 1
    assert records[0].action == "rename"
    assert records[0].target_field_id == "title"
    assert records[0].status == "success"


def test_record_batch_records_multiple(trace_service, db_session):
    events = [
        {"stage": "field_transform", "action": "rename", "target_field_id": "a", "reason": "r1"},
        {"stage": "field_transform", "action": "type_cast", "target_field_id": "b", "reason": "r2"},
        {
            "stage": "field_transform",
            "action": "date_format",
            "target_field_id": "c",
            "reason": "r3",
            "status": "warning",
        },
    ]
    count = trace_service.record_batch("task_1", events)
    db_session.commit()

    assert count == 3
    records = db_session.query(TransformTraceRecord).filter(
        TransformTraceRecord.task_id == "task_1"
    ).all()
    assert len(records) == 3


def test_list_traces_returns_conversion_traces(trace_service, db_session):
    trace_service.record_event(
        task_id="task_1",
        stage="field_transform",
        action="merge",
        target_field_id="full_title",
        before={"fields": ["a", "b"]},
        after={"value": "merged"},
        reason="merged fields",
    )
    db_session.commit()

    traces = trace_service.list_traces("task_1")
    assert len(traces) == 1
    assert traces[0].action == "merge"
    assert traces[0].source == {"fields": ["a", "b"]}
    assert traces[0].result == {"value": "merged"}


def test_export_trace_json_writes_file(trace_service, db_session, tmp_path):
    trace_service.record_event(
        task_id="task_1",
        stage="field_transform",
        action="split",
        reason="split field",
    )
    db_session.commit()

    result = trace_service.export_trace_json("task_1")
    assert "events" in result
    assert len(result["events"]) == 1
    assert result["task_id"] == "task_1"


def test_list_traces_empty_for_unknown_task(trace_service):
    traces = trace_service.list_traces("nonexistent")
    assert traces == []
