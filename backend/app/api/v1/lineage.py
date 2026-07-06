from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.tasks import (
    get_task_execution_service,
)
from app.schemas.lineage import LineageGraph, LineageQueryResult
from app.services.lineage_query_service import LineageQueryService
from app.services.task_execution_service import TaskExecutionService

router = APIRouter(prefix="/tasks/{task_id}/lineage", tags=["lineage"])


@router.get("", response_model=LineageGraph)
def get_task_lineage(
    task_id: str,
    service: Annotated[
        TaskExecutionService,
        Depends(get_task_execution_service),
    ],
) -> LineageGraph:
    return _load_graph(task_id, service)


@router.get("/summary")
def get_lineage_summary(
    task_id: str,
    service: Annotated[
        TaskExecutionService,
        Depends(get_task_execution_service),
    ],
) -> dict[str, Any]:
    try:
        return service.read_report(task_id, "lineage-summary")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fields/{field_name}", response_model=LineageQueryResult)
def get_field_lineage(
    task_id: str,
    field_name: str,
    service: Annotated[
        TaskExecutionService,
        Depends(get_task_execution_service),
    ],
    direction: Annotated[
        Literal["upstream", "downstream", "both"],
        Query(),
    ] = "upstream",
    max_depth: Annotated[int, Query(ge=1, le=32)] = 8,
) -> LineageQueryResult:
    try:
        return LineageQueryService().query_field(
            _load_graph(task_id, service),
            field_name,
            direction=direction,
            max_depth=max_depth,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/chunks/{chunk_id}", response_model=LineageQueryResult)
def get_chunk_lineage(
    task_id: str,
    chunk_id: str,
    service: Annotated[
        TaskExecutionService,
        Depends(get_task_execution_service),
    ],
    direction: Annotated[
        Literal["upstream", "downstream", "both"],
        Query(),
    ] = "upstream",
    max_depth: Annotated[int, Query(ge=1, le=32)] = 8,
) -> LineageQueryResult:
    try:
        return LineageQueryService().query_chunk(
            _load_graph(task_id, service),
            chunk_id,
            direction=direction,
            max_depth=max_depth,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/artifacts/{artifact_path:path}", response_model=LineageQueryResult)
def get_artifact_lineage(
    task_id: str,
    artifact_path: str,
    service: Annotated[
        TaskExecutionService,
        Depends(get_task_execution_service),
    ],
    direction: Annotated[
        Literal["upstream", "downstream", "both"],
        Query(),
    ] = "both",
    max_depth: Annotated[int, Query(ge=1, le=32)] = 8,
) -> LineageQueryResult:
    try:
        return LineageQueryService().query_artifact(
            _load_graph(task_id, service),
            artifact_path,
            direction=direction,
            max_depth=max_depth,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _load_graph(
    task_id: str,
    service: TaskExecutionService,
) -> LineageGraph:
    try:
        return LineageGraph.model_validate(service.read_report(task_id, "lineage"))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
