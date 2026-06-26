from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.api import (
    TemplateCatalogItem,
    TemplateCatalogResponse,
    TemplateCreateRequest,
    TemplateStatusResponse,
)
from app.schemas.mapping_template import MappingTemplate
from app.services.catalog_governance_service import CatalogGovernanceService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_catalog_service(
    db: Annotated[Session, Depends(get_db)],
) -> CatalogGovernanceService:
    return CatalogGovernanceService(db=db)


@router.get("", response_model=TemplateCatalogResponse)
def list_templates(
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> TemplateCatalogResponse:
    records = service.list_template_records()
    return TemplateCatalogResponse(
        items=[
            TemplateCatalogItem(
                template_id=record.template_id,
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


@router.post("", response_model=TemplateCatalogItem)
def create_template(
    request: Annotated[TemplateCreateRequest, Body()],
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> TemplateCatalogItem:
    try:
        record = service.create_template(request.template, status=request.status)
        return TemplateCatalogItem(
            template_id=record.template_id,
            schema_id=record.schema_id,
            name=record.name,
            version=record.version,
            status=record.status,
            content_hash=record.content_hash,
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{template_id}", response_model=MappingTemplate)
def get_template(
    template_id: str,
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
    version: Annotated[str | None, Query()] = None,
) -> MappingTemplate:
    try:
        return service.load_template(template_id, version=version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{template_id}/versions/{version}/activate", response_model=TemplateStatusResponse)
def activate_template(
    template_id: str,
    version: str,
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> TemplateStatusResponse:
    try:
        record = service.activate_template(template_id, version)
        return TemplateStatusResponse(
            template_id=record.template_id,
            version=record.version,
            status=record.status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{template_id}/versions/{version}/archive", response_model=TemplateStatusResponse)
def archive_template(
    template_id: str,
    version: str,
    service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> TemplateStatusResponse:
    try:
        record = service.archive_template(template_id, version)
        return TemplateStatusResponse(
            template_id=record.template_id,
            version=record.version,
            status=record.status,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
