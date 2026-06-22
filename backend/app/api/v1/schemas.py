from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.errors import SchemaInvalidError
from app.schemas.api import (
    SchemaCreateRequest,
    SchemaCreateResponse,
    SchemaListItem,
    SchemaListResponse,
)
from app.schemas.target_schema import TargetSchema
from app.services.schema_service import SchemaService
from app.services.storage_service import StorageService
from app.validators.schema_validator import SchemaValidationError

router = APIRouter(prefix="/schemas", tags=["schemas"])


def get_schema_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> SchemaService:
    return SchemaService(db=db, storage=storage)


@router.post("", response_model=SchemaCreateResponse)
def create_schema(
    request: Annotated[SchemaCreateRequest, Body()],
    service: Annotated[SchemaService, Depends(get_schema_service)],
) -> SchemaCreateResponse:
    try:
        record = service.create_schema(request.target_schema)
    except SchemaValidationError as exc:
        raise SchemaInvalidError(str(exc)) from exc
    return SchemaCreateResponse(schema_id=record.schema_id, status="created")


@router.get("", response_model=SchemaListResponse)
def list_schemas(
    service: Annotated[SchemaService, Depends(get_schema_service)],
) -> SchemaListResponse:
    items = []
    for record in service.list_schemas():
        schema = service.parse_schema(record)
        items.append(
            SchemaListItem(
                schema_id=record.schema_id,
                name=record.name,
                version=record.version,
                fields_count=len(schema.fields),
            )
        )
    return SchemaListResponse(items=items)


@router.get("/{schema_id}", response_model=TargetSchema)
def get_schema(
    schema_id: str,
    service: Annotated[SchemaService, Depends(get_schema_service)],
) -> TargetSchema:
    record = service.get_schema(schema_id)
    if record is None:
        raise HTTPException(status_code=404, detail="schema not found")
    return service.parse_schema(record)
