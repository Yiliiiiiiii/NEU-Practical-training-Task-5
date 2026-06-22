from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.api import (
    TemplateCreateRequest,
    TemplateListItem,
    TemplateListResponse,
    TemplateSaveResponse,
)
from app.schemas.mapping_template import MappingTemplate
from app.services.storage_service import StorageService
from app.services.template_service import TemplateService, TemplateValidationError

router = APIRouter(prefix="/templates", tags=["templates"])


def get_template_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TemplateService:
    return TemplateService(db=db, storage=storage)


@router.post("", response_model=TemplateSaveResponse)
def create_template(
    request: Annotated[TemplateCreateRequest, Body()],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> TemplateSaveResponse:
    return _save_template(request.template, service)


@router.put("/{template_id}", response_model=TemplateSaveResponse)
def update_template(
    template_id: str,
    request: Annotated[TemplateCreateRequest, Body()],
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> TemplateSaveResponse:
    if template_id != request.template.template_id:
        raise HTTPException(status_code=400, detail="template_id path/body mismatch")
    return _save_template(request.template, service)


@router.get("", response_model=TemplateListResponse)
def list_templates(
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> TemplateListResponse:
    items = []
    for record in service.list_templates():
        template = service.parse_template(record)
        items.append(
            TemplateListItem(
                template_id=record.template_id,
                schema_id=record.schema_id,
                name=record.name,
                version=record.version,
                aliases_count=len(template.aliases),
                rules_count=len(template.transform_rules),
            )
        )
    return TemplateListResponse(items=items)


@router.get("/{template_id}", response_model=MappingTemplate)
def get_template(
    template_id: str,
    service: Annotated[TemplateService, Depends(get_template_service)],
) -> MappingTemplate:
    record = service.get_template(template_id)
    if record is None:
        raise HTTPException(status_code=404, detail="template not found")
    return service.parse_template(record)


def _save_template(template: MappingTemplate, service: TemplateService) -> TemplateSaveResponse:
    try:
        record = service.save_template(template)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TemplateSaveResponse(template_id=record.template_id, status="saved")
