from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.db.models import ReviewRecord
from app.schemas.api import (
    ReviewDecisionRequest,
    ReviewListResponse,
    ReviewRecordResponse,
)
from app.schemas.review_workbench import (
    BatchReviewRequest,
    BatchReviewResponse,
    ReviewGroupedResponse,
    ReviewImpactPreview,
    ReviewSummaryResponse,
)
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService
from app.services.review_workbench_service import ReviewWorkbenchService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_workflow_service(
    db: Annotated[Session, Depends(get_db)],
) -> ReviewKnowledgeWorkflowService:
    return ReviewKnowledgeWorkflowService(db=db)


def get_review_workbench_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> ReviewWorkbenchService:
    return ReviewWorkbenchService(db=db, storage=storage)


@router.get("", response_model=ReviewListResponse)
def list_reviews(
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
    status: Annotated[str | None, Query()] = None,
) -> ReviewListResponse:
    records = service.list_reviews(status=status)
    return ReviewListResponse(
        items=[review_response(record) for record in records],
        total=len(records),
    )


@router.get("/summary", response_model=ReviewSummaryResponse)
def review_summary(
    service: Annotated[
        ReviewWorkbenchService,
        Depends(get_review_workbench_service),
    ],
) -> ReviewSummaryResponse:
    return service.summary()


@router.get("/grouped", response_model=ReviewGroupedResponse)
def grouped_reviews(
    service: Annotated[
        ReviewWorkbenchService,
        Depends(get_review_workbench_service),
    ],
    group_by: str = "schema_id",
) -> ReviewGroupedResponse:
    try:
        return service.grouped(group_by)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch-approve", response_model=BatchReviewResponse)
def batch_approve_reviews(
    request: Annotated[BatchReviewRequest, Body()],
    service: Annotated[
        ReviewWorkbenchService,
        Depends(get_review_workbench_service),
    ],
) -> BatchReviewResponse:
    try:
        return service.batch_approve(
            request.review_ids,
            reviewer=request.reviewer,
            comment=request.comment,
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/batch-reject", response_model=BatchReviewResponse)
def batch_reject_reviews(
    request: Annotated[BatchReviewRequest, Body()],
    service: Annotated[
        ReviewWorkbenchService,
        Depends(get_review_workbench_service),
    ],
) -> BatchReviewResponse:
    try:
        return service.batch_reject(
            request.review_ids,
            reviewer=request.reviewer,
            comment=request.comment,
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{review_id}", response_model=ReviewRecordResponse)
def get_review(
    review_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> ReviewRecordResponse:
    try:
        return review_response(service.get_review(review_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{review_id}/impact-preview", response_model=ReviewImpactPreview)
def impact_preview(
    review_id: str,
    service: Annotated[
        ReviewWorkbenchService,
        Depends(get_review_workbench_service),
    ],
) -> ReviewImpactPreview:
    try:
        return service.impact_preview(review_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{review_id}/approve", response_model=ReviewRecordResponse)
def approve_review(
    review_id: str,
    request: Annotated[ReviewDecisionRequest, Body()],
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> ReviewRecordResponse:
    try:
        record, _candidate = service.approve_review(
            review_id,
            reviewer=request.reviewer,
            comment=request.comment,
            create_knowledge_candidate=request.create_knowledge_candidate,
        )
        return review_response(record)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{review_id}/reject", response_model=ReviewRecordResponse)
def reject_review(
    review_id: str,
    request: Annotated[ReviewDecisionRequest, Body()],
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
    workbench: Annotated[
        ReviewWorkbenchService,
        Depends(get_review_workbench_service),
    ],
) -> ReviewRecordResponse:
    try:
        record = service.reject_review(
            review_id,
            reviewer=request.reviewer,
            comment=request.comment,
        )
        if record.source_field_name and record.target_field_id:
            workbench.record_negative_rule(
                record,
                reason=request.comment or record.reason or "human rejection",
            )
        return review_response(record)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def review_response(record: ReviewRecord) -> ReviewRecordResponse:
    return ReviewRecordResponse(
        review_id=record.review_id,
        task_id=record.task_id,
        doc_id=record.doc_id,
        schema_id=record.schema_id,
        template_id=record.template_id,
        source_field_name=record.source_field_name,
        source_path=record.source_path,
        target_field_id=record.target_field_id,
        suggested_by=record.suggested_by,
        confidence=record.confidence,
        reason=record.reason,
        status=record.status,
        reviewer=record.reviewer,
        review_comment=record.review_comment,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )
