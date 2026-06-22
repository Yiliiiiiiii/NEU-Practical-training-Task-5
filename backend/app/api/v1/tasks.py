from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.errors import (
    MappingReviewRequiredError,
    PackageNotReadyError,
    TaskStateError,
)
from app.schemas.api import (
    CanonicalResponse,
    ConsistencyReportResponse,
    ConvertRequest,
    ConvertResponse,
    PackageRequest,
    PackageResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskListItem,
    TaskListResponse,
    TraceListResponse,
    ValidationReportResponse,
)
from app.services.canonical_service import CanonicalService
from app.services.conversion_service import ConversionService
from app.services.package_service import PackageService
from app.services.storage_service import StorageService
from app.services.task_service import TaskService
from app.services.trace_service import TraceService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TaskService:
    return TaskService(db=db, storage=storage)


def get_canonical_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> CanonicalService:
    return CanonicalService(db=db, storage=storage)


def get_conversion_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> ConversionService:
    return ConversionService(db=db, storage=storage)


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


@router.post("/{task_id}/convert", response_model=ConvertResponse)
def convert_task(
    task_id: str,
    request: Annotated[ConvertRequest, Body()],
    service: Annotated[ConversionService, Depends(get_conversion_service)],
) -> ConvertResponse:
    try:
        status, outputs = service.convert(
            task_id=task_id,
            render_outputs=request.render_outputs,
            chunk_size=request.chunk_size,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "requires review" in message:
            raise MappingReviewRequiredError(message) from exc
        raise TaskStateError(message) from exc
    return ConvertResponse(task_id=task_id, status=status, outputs=outputs)


@router.get("/{task_id}/canonical", response_model=CanonicalResponse)
def get_canonical(
    task_id: str,
    canonical_svc: Annotated[CanonicalService, Depends(get_canonical_service)],
) -> CanonicalResponse:
    try:
        model = canonical_svc.get_canonical(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CanonicalResponse.model_validate(model.model_dump(mode="json"))


def get_package_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> PackageService:
    return PackageService(db=db, storage=storage)


def get_trace_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TraceService:
    return TraceService(db=db, storage=storage)


@router.post("/{task_id}/package", response_model=PackageResponse)
def create_package(
    task_id: str,
    request: Annotated[PackageRequest, Body()],
    service: Annotated[PackageService, Depends(get_package_service)],
) -> PackageResponse:
    try:
        result = service.create_package(task_id, request.package_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "not ready" in message or "missing" in message:
            raise PackageNotReadyError(message) from exc
        raise TaskStateError(message) from exc
    return PackageResponse(**result)


@router.get("/{task_id}/package/download")
def download_package(
    task_id: str,
    service: Annotated[PackageService, Depends(get_package_service)],
):
    from fastapi.responses import FileResponse
    try:
        path = service.get_download_path(task_id)
        record = service.get_package(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path=str(path),
        media_type="application/zip",
        filename="standard_package.zip",
        headers={"X-SHA256": record.sha256 or ""},
    )


@router.get("/{task_id}/reports/validation", response_model=ValidationReportResponse)
def get_validation_report(
    task_id: str,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> ValidationReportResponse:
    storage = service.storage
    try:
        data = storage.read_json(f"tasks/{task_id}/validation_report.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="validation report not found") from exc
    return ValidationReportResponse(**data)


@router.get("/{task_id}/reports/consistency", response_model=ConsistencyReportResponse)
def get_consistency_report(
    task_id: str,
    service: Annotated[PackageService, Depends(get_package_service)],
) -> ConsistencyReportResponse:
    storage = service.storage
    try:
        data = storage.read_json(f"tasks/{task_id}/consistency_report.json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="consistency report not found") from exc
    return ConsistencyReportResponse(**data)


@router.get("/{task_id}/trace", response_model=TraceListResponse)
def get_trace(
    task_id: str,
    trace_svc: Annotated[TraceService, Depends(get_trace_service)],
    task_svc: Annotated[TaskService, Depends(get_task_service)],
) -> TraceListResponse:
    if task_svc.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    traces = trace_svc.list_traces(task_id)
    return TraceListResponse(
        task_id=task_id,
        events=[t.model_dump(mode="json") for t in traces],
    )
