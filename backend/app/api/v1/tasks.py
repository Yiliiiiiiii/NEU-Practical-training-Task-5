from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.api import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskExecuteResponse,
    TaskListItem,
    TaskListResponse,
)
from app.services.storage_service import StorageService
from app.services.task_execution_service import TaskExecutionService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TaskService:
    return TaskService(db=db, storage=storage)


def get_task_execution_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TaskExecutionService:
    return TaskExecutionService(db=db, storage=storage)


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


@router.post("/{task_id}/execute", response_model=TaskExecuteResponse)
def execute_task(
    task_id: str,
    service: Annotated[TaskExecutionService, Depends(get_task_execution_service)],
) -> TaskExecuteResponse:
    try:
        result = service.execute_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskExecuteResponse(
        task_id=result.task_id,
        status=result.status,
        report_paths=result.report_paths,
        package_zip_path=result.package_zip_path,
        review_required_count=result.review_required_count,
        unmapped_required_count=result.unmapped_required_count,
    )


@router.get("/{task_id}/reports/{report_name}")
def get_task_report(
    task_id: str,
    report_name: str,
    service: Annotated[TaskExecutionService, Depends(get_task_execution_service)],
) -> dict[str, Any]:
    try:
        return service.read_report(task_id, report_name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{task_id}/package")
def get_task_package(
    task_id: str,
    service: Annotated[TaskExecutionService, Depends(get_task_execution_service)],
) -> dict[str, Any]:
    try:
        return service.package_metadata(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{task_id}/package/download")
def download_task_package(
    task_id: str,
    service: Annotated[TaskExecutionService, Depends(get_task_execution_service)],
) -> FileResponse:
    try:
        path = service.package_zip_path(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(path, media_type="application/zip", filename=path.name)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(
    task_id: str,
    service: Annotated[TaskService, Depends(get_task_service)],
    execution_service: Annotated[
        TaskExecutionService,
        Depends(get_task_execution_service),
    ],
) -> TaskDetailResponse:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    snapshot = execution_service.execution_snapshot(task)
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
        report_paths=snapshot.get("report_paths", {}),
        package_zip_path=snapshot.get("package_zip_path"),
    )
