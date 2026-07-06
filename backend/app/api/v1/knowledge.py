import json
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.db.models import KnowledgeCandidateRecord, KnowledgePackRecord
from app.schemas.api import (
    KnowledgeCandidateListResponse,
    KnowledgeCandidateResponse,
    KnowledgeMetricsResponse,
    KnowledgePackCreateRequest,
    KnowledgePackListResponse,
    KnowledgePackResponse,
)
from app.schemas.mapping_template import MappingTemplate
from app.schemas.review_workbench import (
    KnowledgeConflictResponse,
    KnowledgePackDiffResponse,
    KnowledgePackImpactResponse,
    KnowledgePackRollbackResponse,
)
from app.services.knowledge_pack_governance_service import (
    KnowledgePackGovernanceService,
)
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_review_workflow_service(
    db: Annotated[Session, Depends(get_db)],
) -> ReviewKnowledgeWorkflowService:
    return ReviewKnowledgeWorkflowService(db=db)


def get_pack_governance_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> KnowledgePackGovernanceService:
    return KnowledgePackGovernanceService(db=db, storage=storage)


@router.get("/candidates", response_model=KnowledgeCandidateListResponse)
def list_candidates(
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
    status: Annotated[str | None, Query()] = None,
) -> KnowledgeCandidateListResponse:
    candidates = service.list_candidates(status=status)
    return KnowledgeCandidateListResponse(
        items=[candidate_response(candidate) for candidate in candidates],
        total=len(candidates),
    )


@router.post("/candidates/{candidate_id}/accept", response_model=KnowledgeCandidateResponse)
def accept_candidate(
    candidate_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> KnowledgeCandidateResponse:
    try:
        return candidate_response(service.accept_candidate(candidate_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/reject", response_model=KnowledgeCandidateResponse)
def reject_candidate(
    candidate_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> KnowledgeCandidateResponse:
    try:
        return candidate_response(service.reject_candidate(candidate_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/packs", response_model=KnowledgePackListResponse)
def list_packs(
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
    status: Annotated[str | None, Query()] = None,
) -> KnowledgePackListResponse:
    packs = service.list_packs(status=status)
    return KnowledgePackListResponse(
        items=[pack_response(service, pack) for pack in packs],
        total=len(packs),
    )


@router.post("/packs", response_model=KnowledgePackResponse)
def create_pack(
    request: Annotated[KnowledgePackCreateRequest, Body()],
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> KnowledgePackResponse:
    pack = service.create_pack(
        schema_id=request.schema_id,
        template_id=request.template_id,
        name=request.name,
        created_by=request.created_by,
    )
    return pack_response(service, pack)


@router.post("/packs/{pack_id}/activate", response_model=KnowledgePackResponse)
def activate_pack(
    pack_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
    governance: Annotated[
        KnowledgePackGovernanceService,
        Depends(get_pack_governance_service),
    ],
) -> KnowledgePackResponse:
    try:
        governance.assert_can_activate(pack_id)
        return pack_response(service, service.activate_pack(pack_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/packs/{pack_id}/archive", response_model=KnowledgePackResponse)
def archive_pack(
    pack_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> KnowledgePackResponse:
    try:
        return pack_response(service, service.archive_pack(pack_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/packs/{pack_id}/diff", response_model=KnowledgePackDiffResponse)
def pack_diff(
    pack_id: str,
    service: Annotated[
        KnowledgePackGovernanceService,
        Depends(get_pack_governance_service),
    ],
) -> KnowledgePackDiffResponse:
    try:
        return service.diff(pack_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/packs/{pack_id}/impact", response_model=KnowledgePackImpactResponse)
def pack_impact(
    pack_id: str,
    service: Annotated[
        KnowledgePackGovernanceService,
        Depends(get_pack_governance_service),
    ],
) -> KnowledgePackImpactResponse:
    try:
        return service.impact(pack_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/packs/{pack_id}/rollback", response_model=KnowledgePackRollbackResponse)
def rollback_pack(
    pack_id: str,
    service: Annotated[
        KnowledgePackGovernanceService,
        Depends(get_pack_governance_service),
    ],
) -> KnowledgePackRollbackResponse:
    try:
        return service.rollback(pack_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conflicts", response_model=KnowledgeConflictResponse)
def knowledge_conflicts(
    service: Annotated[
        KnowledgePackGovernanceService,
        Depends(get_pack_governance_service),
    ],
) -> KnowledgeConflictResponse:
    return service.conflicts()


@router.get("/effective-template", response_model=MappingTemplate)
def effective_template(
    schema_id: str,
    template_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> MappingTemplate:
    try:
        return service.effective_template(schema_id=schema_id, template_id=template_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/metrics", response_model=KnowledgeMetricsResponse)
def metrics(
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> KnowledgeMetricsResponse:
    return KnowledgeMetricsResponse(**service.metrics())


def candidate_response(candidate: KnowledgeCandidateRecord) -> KnowledgeCandidateResponse:
    return KnowledgeCandidateResponse(
        candidate_id=candidate.candidate_id,
        review_id=candidate.review_id,
        schema_id=candidate.schema_id,
        template_id=candidate.template_id,
        target_field_id=candidate.target_field_id,
        alias=candidate.alias,
        candidate_type=candidate.candidate_type,
        support_count=candidate.support_count,
        badcase_hit=candidate.badcase_hit,
        status=candidate.status,
        created_at=candidate.created_at.isoformat(),
        updated_at=candidate.updated_at.isoformat(),
    )


def pack_response(
    service: ReviewKnowledgeWorkflowService,
    pack: KnowledgePackRecord,
) -> KnowledgePackResponse:
    return KnowledgePackResponse(
        pack_id=pack.pack_id,
        name=pack.name,
        schema_id=pack.schema_id,
        template_id=pack.template_id,
        version=pack.version,
        status=pack.status,
        created_by=pack.created_by,
        metadata=json.loads(pack.metadata_json or "{}"),
        items=[
            {
                "item_id": item.item_id,
                "item_type": item.item_type,
                "target_field_id": item.target_field_id,
                "value": json.loads(item.value_json),
                "candidate_id": item.candidate_id,
            }
            for item in service.pack_items(pack.pack_id)
        ],
        created_at=pack.created_at.isoformat(),
        activated_at=pack.activated_at.isoformat() if pack.activated_at else None,
        updated_at=pack.updated_at.isoformat(),
    )
