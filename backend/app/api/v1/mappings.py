from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_settings,
    get_storage_service,
    get_task_mutation_registry,
)
from app.clients.llm_client import LLMClient
from app.config import Settings
from app.errors import TaskStateError
from app.schemas.api import (
    CandidateListItem,
    CandidateListResponse,
    GenerateCandidatesRequest,
    GenerateCandidatesResponse,
    MappingListItem,
    MappingListResponse,
    MappingReviewRequest,
    MappingReviewResponse,
    MappingRunRequest,
    MappingRunResponse,
)
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.review_service import ReviewService
from app.services.storage_service import StorageService
from app.services.task_lock_service import TaskMutationConflict, TaskMutationRegistry

router = APIRouter(prefix="/tasks/{task_id}", tags=["mappings"])


def get_candidate_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> CandidateService:
    return CandidateService(db=db, storage=storage)


def get_mapping_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MappingService:
    return MappingService(
        db=db,
        storage=storage,
        llm_client=LLMClient.from_settings(settings),
    )


def get_review_service(
    db: Annotated[Session, Depends(get_db)],
) -> ReviewService:
    return ReviewService(db=db)


@router.post("/generate-candidates", response_model=GenerateCandidatesResponse)
def generate_candidates(
    task_id: str,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
    mutation_registry: Annotated[
        TaskMutationRegistry, Depends(get_task_mutation_registry)
    ],
    request: Annotated[GenerateCandidatesRequest | None, Body()] = None,
) -> GenerateCandidatesResponse:
    request = request or GenerateCandidatesRequest()
    try:
        with mutation_registry.task_mutation(task_id):
            candidates = service.generate_candidates(
                task_id=task_id,
                include_metadata=request.include_metadata,
                include_blocks=request.include_blocks,
                include_tables=request.include_tables,
            )
    except TaskMutationConflict as exc:
        raise TaskStateError(str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return GenerateCandidatesResponse(
        task_id=task_id,
        candidate_count=len(candidates),
        status="candidates_ready",
    )


@router.get("/candidates", response_model=CandidateListResponse)
def list_candidates(
    task_id: str,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> CandidateListResponse:
    try:
        candidates = service.list_candidates(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CandidateListResponse(
        items=[
            CandidateListItem(
                candidate_id=candidate.candidate_id,
                task_id=candidate.task_id,
                doc_id=candidate.doc_id,
                source_path=candidate.source_path,
                source_name=candidate.source_name,
                display_name=candidate.display_name,
                value_sample=candidate.value_sample,
                inferred_type=candidate.inferred_type,
                source_blocks=candidate.source_blocks,
                confidence=candidate.confidence,
                evidence=candidate.evidence,
            )
            for candidate in candidates
        ]
    )


@router.post("/map", response_model=MappingRunResponse)
def run_mapping(
    task_id: str,
    request: Annotated[MappingRunRequest, Body()],
    service: Annotated[MappingService, Depends(get_mapping_service)],
    mutation_registry: Annotated[
        TaskMutationRegistry, Depends(get_task_mutation_registry)
    ],
) -> MappingRunResponse:
    try:
        with mutation_registry.task_mutation(task_id):
            mappings, report, status = service.run_mapping(
                task_id=task_id,
                review_threshold=request.review_threshold,
                enable_llm_fallback=request.enable_llm_fallback,
            )
    except TaskMutationConflict as exc:
        raise TaskStateError(str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MappingRunResponse(
        task_id=task_id,
        mapped_count=report.summary["mapped_fields"],
        review_required_count=report.summary["review_required"],
        status=status,
    )


@router.get("/mappings", response_model=MappingListResponse)
def list_mappings(
    task_id: str,
    service: Annotated[MappingService, Depends(get_mapping_service)],
) -> MappingListResponse:
    try:
        mappings = service.list_mappings(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MappingListResponse(
        items=[
            MappingListItem(
                mapping_id=mapping.mapping_id,
                task_id=mapping.task_id,
                candidate_id=mapping.candidate_id,
                source_name=mapping.source_field.source_name,
                source_path=mapping.source_field.source_path,
                target_field_id=mapping.target_field_id,
                target_field_name=mapping.target_field_name,
                method=mapping.method,
                confidence=mapping.confidence,
                status=mapping.status,
                need_review=mapping.need_review,
                evidence=mapping.evidence,
            )
            for mapping in mappings
        ]
    )


@router.post("/mappings/review", response_model=MappingReviewResponse)
def review_mappings(
    task_id: str,
    request: Annotated[MappingReviewRequest, Body()],
    service: Annotated[ReviewService, Depends(get_review_service)],
    mutation_registry: Annotated[
        TaskMutationRegistry, Depends(get_task_mutation_registry)
    ],
) -> MappingReviewResponse:
    try:
        with mutation_registry.task_mutation(task_id):
            updated = service.save_mapping_reviews(task_id=task_id, reviews=request.reviews)
    except TaskMutationConflict as exc:
        raise TaskStateError(str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MappingReviewResponse(task_id=task_id, updated=updated, status="review_saved")
