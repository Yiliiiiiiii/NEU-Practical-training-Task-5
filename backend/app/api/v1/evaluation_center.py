from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_storage_service
from app.schemas.evaluation_center import (
    DatasetRegistryResponse,
    EvaluationRun,
    EvaluationRunListResponse,
    EvaluationRunRequest,
    EvaluationScorecard,
    MetricRegistryResponse,
)
from app.services.evaluation_center_service import EvaluationCenterService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/evaluation-center", tags=["evaluation-center"])


def get_evaluation_center_service(
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> EvaluationCenterService:
    return EvaluationCenterService(storage)


@router.get("/datasets", response_model=DatasetRegistryResponse)
def list_datasets(
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> DatasetRegistryResponse:
    return DatasetRegistryResponse(items=service.list_datasets())


@router.get("/metrics", response_model=MetricRegistryResponse)
def list_metrics(
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> MetricRegistryResponse:
    return MetricRegistryResponse(items=service.list_metrics())


@router.get("/runs", response_model=EvaluationRunListResponse)
def list_runs(
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> EvaluationRunListResponse:
    items = service.list_runs()
    return EvaluationRunListResponse(items=items, total=len(items))


@router.get("/runs/{run_id}", response_model=EvaluationRun)
def get_run(
    run_id: str,
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> EvaluationRun:
    try:
        return service.get_run(run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/reports/{report_key}", response_class=FileResponse)
def get_run_report(
    run_id: str,
    report_key: str,
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> FileResponse:
    try:
        return FileResponse(service.resolve_report_path(run_id, report_key))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scorecard", response_model=EvaluationScorecard)
def scorecard(
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> EvaluationScorecard:
    return service.scorecard()


@router.post("/run", response_model=EvaluationRun)
def register_run(
    request: Annotated[EvaluationRunRequest, Body()],
    service: Annotated[
        EvaluationCenterService,
        Depends(get_evaluation_center_service),
    ],
) -> EvaluationRun:
    try:
        if request.metrics:
            return service.register_run(
                dataset_id=request.dataset_id,
                eval_type=request.eval_type,
                metrics=request.metrics,
                report_paths=request.report_paths,
                git_commit=request.git_commit,
            )
        return service.register_from_report(
            dataset_id=request.dataset_id,
            eval_type=request.eval_type,
            report_paths=request.report_paths,
            git_commit=request.git_commit,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
