from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.deps import get_storage_service
from app.schemas.schema_draft import (
    DraftRiskReport,
    FieldDiscoveryResult,
    SchemaDraftDiscoverRequest,
    SchemaDraftExportResponse,
    SchemaDraftGenerateRequest,
    SchemaDraftPackage,
)
from app.services.schema_draft_workflow_service import SchemaDraftWorkflowService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/schema-drafts", tags=["schema-drafts"])


def get_schema_draft_workflow(
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> SchemaDraftWorkflowService:
    return SchemaDraftWorkflowService(storage)


@router.post("/discover", response_model=FieldDiscoveryResult)
def discover_fields(
    request: Annotated[SchemaDraftDiscoverRequest, Body()],
    service: Annotated[
        SchemaDraftWorkflowService,
        Depends(get_schema_draft_workflow),
    ],
) -> FieldDiscoveryResult:
    return service.discover(request.documents)


@router.post("/generate", response_model=SchemaDraftPackage)
def generate_schema_draft(
    request: Annotated[SchemaDraftGenerateRequest, Body()],
    service: Annotated[
        SchemaDraftWorkflowService,
        Depends(get_schema_draft_workflow),
    ],
) -> SchemaDraftPackage:
    try:
        return service.generate(
            request.documents,
            schema_id=request.schema_id,
            schema_name=request.schema_name,
            template_id=request.template_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{draft_id}", response_model=SchemaDraftPackage)
def get_schema_draft(
    draft_id: str,
    service: Annotated[
        SchemaDraftWorkflowService,
        Depends(get_schema_draft_workflow),
    ],
) -> SchemaDraftPackage:
    try:
        return service.get(draft_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{draft_id}/validate", response_model=DraftRiskReport)
def validate_schema_draft(
    draft_id: str,
    service: Annotated[
        SchemaDraftWorkflowService,
        Depends(get_schema_draft_workflow),
    ],
) -> DraftRiskReport:
    try:
        return service.validate(draft_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{draft_id}/export", response_model=SchemaDraftExportResponse)
def export_schema_draft(
    draft_id: str,
    service: Annotated[
        SchemaDraftWorkflowService,
        Depends(get_schema_draft_workflow),
    ],
) -> SchemaDraftExportResponse:
    try:
        return service.export(draft_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
