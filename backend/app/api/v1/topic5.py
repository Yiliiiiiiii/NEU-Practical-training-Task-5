from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_storage_service
from app.schemas.topic5_convert import Topic5ConvertRequest, Topic5ConvertResponse
from app.services.storage_service import StorageService
from app.services.topic5_conversion_service import Topic5ConversionService

router = APIRouter(prefix="/topic5", tags=["topic5"])


@router.post("/convert", response_model=Topic5ConvertResponse)
def convert_topic5(
    request: Topic5ConvertRequest,
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> Topic5ConvertResponse:
    try:
        return Topic5ConversionService(storage.root).convert(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/convert/package", response_model=Topic5ConvertResponse)
def convert_topic5_package(
    request: Topic5ConvertRequest,
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> Topic5ConvertResponse:
    try:
        return Topic5ConversionService(storage.root).convert(request, create_package=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
