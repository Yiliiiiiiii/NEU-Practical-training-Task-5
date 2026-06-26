from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import ReviewRecord
from app.schemas.api import (
    ReviewDecisionRequest,
    ReviewListResponse,
    ReviewRecordResponse,
)
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_workflow_service(
    db: Annotated[Session, Depends(get_db)],
) -> ReviewKnowledgeWorkflowService:
    return ReviewKnowledgeWorkflowService(db=db)


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


@router.get("/{review_id}", response_model=ReviewRecordResponse)
def get_review(
    review_id: str,
    service: Annotated[ReviewKnowledgeWorkflowService, Depends(get_review_workflow_service)],
) -> ReviewRecordResponse:
    try:
        return review_response(service.get_review(review_id))
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
) -> ReviewRecordResponse:
    try:
        return review_response(
            service.reject_review(
                review_id,
                reviewer=request.reviewer,
                comment=request.comment,
            )
        )
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
