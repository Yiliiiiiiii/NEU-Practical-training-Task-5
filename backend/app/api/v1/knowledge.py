from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.knowledge import (
    CandidateDecisionRequest,
    CandidateListResponse,
    KnowledgeMetricsResponse,
    KnowledgePackCreateRequest,
    KnowledgePackListResponse,
    KnowledgePackView,
    LearningCandidateView,
    RealRunView,
)
from app.services.knowledge_service import KnowledgeService, KnowledgeValidationError
from app.services.storage_service import StorageService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> KnowledgeService:
    return KnowledgeService(db, storage)


@router.post("/real-runs/from-task/{task_id}", response_model=RealRunView)
def capture_real_run(
    task_id: str,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> RealRunView:
    try:
        return service.capture_real_run(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/real-runs/{real_run_id}/derive", response_model=CandidateListResponse)
def derive_candidates(
    real_run_id: str,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> CandidateListResponse:
    try:
        return CandidateListResponse(
            items=service.derive_learning_candidates(real_run_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/candidates", response_model=CandidateListResponse)
def list_candidates(
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    status: Annotated[str | None, Query()] = None,
) -> CandidateListResponse:
    return CandidateListResponse(items=service.list_candidates(status=status))


@router.post("/candidates/{candidate_id}/decision", response_model=LearningCandidateView)
def decide_candidate(
    candidate_id: str,
    request: CandidateDecisionRequest,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> LearningCandidateView:
    try:
        return service.decide_candidate(candidate_id, request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/packs", response_model=KnowledgePackView)
def create_pack(
    request: KnowledgePackCreateRequest,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgePackView:
    try:
        return service.create_knowledge_pack(request)
    except KnowledgeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/packs/{pack_id}/activate", response_model=KnowledgePackView)
def activate_pack(
    pack_id: str,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgePackView:
    try:
        return service.activate_pack(pack_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/packs", response_model=KnowledgePackListResponse)
def list_packs(
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgePackListResponse:
    return KnowledgePackListResponse(items=service.list_packs())


@router.get("/metrics", response_model=KnowledgeMetricsResponse)
def get_metrics(
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgeMetricsResponse:
    return service.metrics()
