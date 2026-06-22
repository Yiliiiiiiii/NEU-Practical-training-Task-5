from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage_service
from app.schemas.api import (
    DocumentDetailResponse,
    DocumentImportRequest,
    DocumentImportResponse,
    DocumentListItem,
    DocumentListResponse,
)
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> DocumentService:
    return DocumentService(db=db, storage=storage)


@router.post("/import", response_model=DocumentImportResponse)
def import_document(
    request: Annotated[DocumentImportRequest, Body()],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentImportResponse:
    document = service.import_uir(request.uir)
    return DocumentImportResponse(
        doc_id=document.doc_id,
        status="imported",
        block_count=document.block_count,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    service: Annotated[DocumentService, Depends(get_document_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentListResponse:
    documents, total = service.list_documents(page=page, page_size=page_size)
    return DocumentListResponse(
        items=[
            DocumentListItem(
                doc_id=document.doc_id,
                title=document.title,
                block_count=document.block_count,
            )
            for document in documents
        ],
        total=total,
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    doc_id: str,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentDetailResponse:
    document = service.get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    uir = service.read_uir(document)
    blocks = uir.get("blocks", [])
    return DocumentDetailResponse(
        doc_id=document.doc_id,
        metadata=uir.get("metadata", {}),
        blocks_preview=blocks[:5] if isinstance(blocks, list) else [],
    )
