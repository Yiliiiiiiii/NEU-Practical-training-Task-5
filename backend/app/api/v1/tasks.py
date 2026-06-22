from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.api import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskListItem,
    TaskListResponse,
)
from app.services.storage_service import StorageService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TaskService:
    return TaskService(db=db, storage=storage)


@router.post("", response_model=TaskCreateResponse)
def create_task(
    request: Annotated[TaskCreateRequest, Body()],
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskCreateResponse:
    try:
        task = service.create_task(request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TaskCreateResponse(task_id=task.task_id, status=task.status)


@router.get("", response_model=TaskListResponse)
def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TaskListResponse:
    tasks, total = service.list_tasks(page=page, page_size=page_size)
    return TaskListResponse(
        items=[
            TaskListItem(
                task_id=task.task_id,
                doc_id=task.doc_id,
                schema_id=task.schema_id,
                template_id=task.template_id,
                status=task.status,
            )
            for task in tasks
        ],
        total=total,
    )


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
) -> TaskDetailResponse:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    return TaskDetailResponse(
        task_id=task.task_id,
        status=task.status,
        doc_id=task.doc_id,
        schema_id=task.schema_id,
        schema_version=task.schema_version,
        template_id=task.template_id,
        template_version=task.template_version,
        input_hash=task.input_hash,
        options=service.task_options(task),
    )
