import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.api import AuditLogListResponse, AuditLogResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    success: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogListResponse:
    records, total = AuditLogService(db).list_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        success=success,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[
            AuditLogResponse(
                audit_id=record.audit_id,
                created_at=record.created_at.isoformat(),
                action=record.action,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                actor_type=record.actor_type,
                actor_id=record.actor_id,
                api_key_hash_prefix=record.api_key_hash_prefix,
                request_id=record.request_id,
                trace_id=record.trace_id,
                method=record.method,
                path=record.path,
                status_code=record.status_code,
                success=record.success,
                error_code=record.error_code,
                metadata=json.loads(record.metadata_json or "{}"),
            )
            for record in records
        ],
        total=total,
    )
