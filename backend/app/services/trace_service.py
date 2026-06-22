import json

from sqlalchemy.orm import Session

from app.db.models import TransformTraceRecord
from app.schemas.reports import ConversionTrace
from app.services.storage_service import StorageService
from app.utils.ids import new_id


class TraceService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def record_event(
        self,
        task_id: str,
        stage: str,
        action: str,
        target_field_id: str | None = None,
        before: dict | None = None,
        after: dict | None = None,
        rule_id: str | None = None,
        reason: str = "",
        status: str = "success",
    ) -> TransformTraceRecord:
        record = TransformTraceRecord(
            trace_id=new_id("trace"),
            task_id=task_id,
            stage=stage,
            action=action,
            target_field_id=target_field_id,
            before_json=json.dumps(before or {}, ensure_ascii=False),
            after_json=json.dumps(after or {}, ensure_ascii=False),
            rule_id=rule_id,
            reason=reason,
            status=status,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def record_batch(self, task_id: str, events: list[dict]) -> int:
        count = 0
        for event in events:
            self.record_event(
                task_id=task_id,
                stage=event.get("stage", ""),
                action=event.get("action", ""),
                target_field_id=event.get("target_field_id"),
                before=event.get("source"),
                after=event.get("result"),
                rule_id=event.get("rule_id"),
                reason=event.get("reason", ""),
                status=event.get("status", "success"),
            )
            count += 1
        return count

    def list_traces(self, task_id: str) -> list[ConversionTrace]:
        records = (
            self.db.query(TransformTraceRecord)
            .filter(TransformTraceRecord.task_id == task_id)
            .order_by(TransformTraceRecord.created_at.asc())
            .all()
        )
        return [self._to_trace(record) for record in records]

    def export_trace_json(self, task_id: str) -> dict:
        traces = self.list_traces(task_id)
        trace_data = {
            "task_id": task_id,
            "events": [t.model_dump(mode="json") for t in traces],
        }
        self.storage.save_json(f"tasks/{task_id}/trace.json", trace_data)
        return trace_data

    @staticmethod
    def _to_trace(record: TransformTraceRecord) -> ConversionTrace:
        return ConversionTrace(
            trace_id=record.trace_id,
            task_id=record.task_id,
            stage=record.stage,
            action=record.action,
            target_field_id=record.target_field_id,
            source=json.loads(record.before_json or "{}"),
            result=json.loads(record.after_json or "{}"),
            rule_id=record.rule_id,
            reason=record.reason,
            status=record.status,
            created_at=record.created_at.isoformat() if record.created_at else "",
        )
