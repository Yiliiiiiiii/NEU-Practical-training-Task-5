from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.reports import MappingReport
from app.services.mapping_service import MappingService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/tasks/{task_id}/reports", tags=["reports"])


def get_mapping_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> MappingService:
    return MappingService(db=db, storage=storage)


@router.get("/mapping", response_model=MappingReport)
def get_mapping_report(
    task_id: str,
    service: Annotated[MappingService, Depends(get_mapping_service)],
) -> MappingReport:
    try:
        return service.read_mapping_report(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="mapping report not found") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
