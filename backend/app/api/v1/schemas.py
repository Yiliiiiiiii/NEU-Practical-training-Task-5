from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.api import (
    SchemaCatalogItem,
    SchemaCatalogResponse,
    SchemaCreateRequest,
    SchemaStatusResponse,
)
from app.schemas.target_schema import TargetSchema
from app.services.catalog_governance_service import CatalogGovernanceService

router = APIRouter(prefix="/schemas", tags=["schemas"])


def get_catalog_service(
    db: Annotated[Session, Depends(get_db)],
) -> CatalogGovernanceService:
    return CatalogGovernanceService(db=db)


@router.get("", response_model=SchemaCatalogResponse)
def list_schemas(
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> SchemaCatalogResponse:
    records = service.list_schema_records()
    return SchemaCatalogResponse(
        items=[
            SchemaCatalogItem(
                schema_id=record.schema_id,
                name=record.name,
                version=record.version,
                status=record.status,
                content_hash=record.content_hash,
            )
            for record in records
        ],
        total=len(records),
    )


@router.post("", response_model=SchemaCatalogItem)
def create_schema(
    request: Annotated[SchemaCreateRequest, Body()],
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> SchemaCatalogItem:
    try:
        record = service.create_schema(request.target_schema, status=request.status)
        return SchemaCatalogItem(
            schema_id=record.schema_id,
            name=record.name,
            version=record.version,
            status=record.status,
            content_hash=record.content_hash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{schema_id}", response_model=TargetSchema)
def get_schema(
    schema_id: str,
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
    version: Annotated[str | None, Query()] = None,
) -> TargetSchema:
    try:
        return service.load_schema(schema_id, version=version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{schema_id}/versions/{version}/activate", response_model=SchemaStatusResponse)
def activate_schema(
    schema_id: str,
    version: str,
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> SchemaStatusResponse:
    try:
        record = service.activate_schema(schema_id, version)
        return SchemaStatusResponse(
            schema_id=record.schema_id,
            version=record.version,
            status=record.status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{schema_id}/versions/{version}/archive", response_model=SchemaStatusResponse)
def archive_schema(
    schema_id: str,
    version: str,
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> SchemaStatusResponse:
    try:
        record = service.archive_schema(schema_id, version)
        return SchemaStatusResponse(
            schema_id=record.schema_id,
            version=record.version,
            status=record.status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
