import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLogRecord
from app.utils.redaction import redact_sensitive_values


class AuditLogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        success: bool = True,
        error_code: str | None = None,
        api_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogRecord:
        record = AuditLogRecord(
            audit_id=f"audit_{uuid4().hex}",
            created_at=datetime.now(UTC),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            api_key_hash_prefix=self._hash_prefix(api_key),
            method=method,
            path=path,
            status_code=status_code,
            success=success,
            error_code=error_code,
            metadata_json=json.dumps(
                redact_sensitive_values(metadata or {}),
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_logs(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        success: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLogRecord], int]:
        statement = select(AuditLogRecord)
        if entity_type:
            statement = statement.where(AuditLogRecord.entity_type == entity_type)
        if entity_id:
            statement = statement.where(AuditLogRecord.entity_id == entity_id)
        if action:
            statement = statement.where(AuditLogRecord.action == action)
        if success is not None:
            statement = statement.where(AuditLogRecord.success == success)
        records = list(
            self.db.scalars(
                statement.order_by(AuditLogRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = len(list(self.db.scalars(statement)))
        return records, total

    @staticmethod
    def _hash_prefix(api_key: str | None) -> str | None:
        if not api_key:
            return None
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
