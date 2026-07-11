from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.base import AdapterInput
from app.adapters.registry import build_default_registry
from app.api.deps import get_db, get_settings, get_storage_service
from app.config import Settings
from app.schemas.adapter import (
    AdapterDetectRequest,
    AdapterDetectResponse,
    AdapterListResponse,
    AdapterSelectionItem,
)
from app.schemas.api import TaskCreateRequest
from app.schemas.external_uir import (
    AdapterReport,
    ExternalUIRConvertRequest,
    ExternalUIRConvertResponse,
    ExternalUIRCreateTaskRequest,
    ExternalUIRCreateTaskResponse,
    ExternalUIRDocumentSummary,
    ExternalUIRImportRequest,
    ExternalUIRImportResponse,
)
from app.schemas.uir import UIRDocument
from app.services.catalog_governance_service import CatalogGovernanceService
from app.services.document_service import DocumentService
from app.services.external_uir_adapter_service import ExternalUIRAdapterService
from app.services.external_uir_llm_service import ExternalUIRLLMSuggestionService
from app.services.schema_router_service import SchemaRouterService
from app.services.storage_service import StorageService
from app.services.task_service import TaskService

router = APIRouter(prefix="/external-uir", tags=["external-uir"])


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> DocumentService:
    return DocumentService(db=db, storage=storage)


def get_task_service(
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TaskService:
    return TaskService(db=db, storage=storage)


def get_catalog_service(
    db: Annotated[Session, Depends(get_db)],
) -> CatalogGovernanceService:
    return CatalogGovernanceService(db=db)


@router.get("/adapters", response_model=AdapterListResponse)
def list_external_uir_adapters() -> AdapterListResponse:
    return AdapterListResponse(items=build_default_registry().list_capabilities())


@router.post("/detect", response_model=AdapterDetectResponse)
def detect_external_uir_adapter(
    request: Annotated[AdapterDetectRequest, Body()],
) -> AdapterDetectResponse:
    selected = build_default_registry().select_adapter(
        AdapterInput(
            payload=request.payload,
            source_system=request.source_system,
            dialect_hint=request.dialect_hint or "auto",
            options=request.options,
        )
    )
    return AdapterDetectResponse(
        selected_adapter=AdapterSelectionItem(
            adapter_id=selected.adapter_id,
            confidence=selected.confidence,
        )
        if selected.adapter_id
        else None,
        alternatives=selected.alternatives,
        review_required=selected.review_required,
        error=selected.error,
    )


@router.post("/convert", response_model=ExternalUIRConvertResponse)
def convert_external_uir(
    request: Annotated[ExternalUIRConvertRequest, Body()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExternalUIRConvertResponse:
    return _convert(request, settings=settings)


@router.post("/import", response_model=ExternalUIRImportResponse)
def import_external_uir(
    request: Annotated[ExternalUIRImportRequest, Body()],
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> ExternalUIRImportResponse:
    converted = _convert(
        ExternalUIRConvertRequest(
            payload=request.payload,
            source_system=request.source_system,
            dialect_hint=request.dialect_hint,
            route_schema=request.route_schema,
            allow_llm=request.allow_llm,
            llm_mode=request.llm_mode,
            dry_run=False,
        ),
        settings=settings,
    )
    document = service.import_uir(converted.standard_uir)
    return ExternalUIRImportResponse(
        doc_id=document.doc_id,
        document=ExternalUIRDocumentSummary(
            doc_id=document.doc_id,
            title=document.title,
            block_count=document.block_count,
        ),
        adapter_report=converted.adapter_report,
        route_report=converted.route_report,
        warnings=converted.warnings,
    )


@router.post("/create-task", response_model=ExternalUIRCreateTaskResponse)
def create_external_uir_task(
    request: Annotated[ExternalUIRCreateTaskRequest, Body()],
    task_service: Annotated[TaskService, Depends(get_task_service)],
    catalog_service: Annotated[CatalogGovernanceService, Depends(get_catalog_service)],
) -> ExternalUIRCreateTaskResponse:
    try:
        catalog_service.load_schema(request.schema_id, version=request.schema_version)
        catalog_service.load_template(request.template_id, version=request.template_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    review_required = bool(request.route_report and request.route_report.review_required)
    warnings = ["route review required"] if review_required else []
    options = {
        **request.options,
        "external_uir": {
            "route_report": request.route_report.model_dump(mode="json")
            if request.route_report
            else None,
            "adapter_report": request.adapter_report.model_dump(mode="json")
            if request.adapter_report
            else None,
            "review_required": review_required,
        },
    }
    try:
        task = task_service.create_task(
            TaskCreateRequest(
                doc_id=request.doc_id,
                schema_id=request.schema_id,
                template_id=request.template_id,
                schema_version=request.schema_version,
                template_version=request.template_version,
                enable_legacy_transform_heuristics=(
                    request.enable_legacy_transform_heuristics
                ),
                options=options,
            )
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ExternalUIRCreateTaskResponse(
        task_id=task.task_id,
        status=task.status,
        review_required=review_required,
        warnings=warnings,
    )


def _convert(
    request: ExternalUIRConvertRequest,
    *,
    settings: Settings,
) -> ExternalUIRConvertResponse:
    adapter = ExternalUIRAdapterService()
    warnings: list[str] = []
    try:
        standard_uir, adapter_report = adapter.adapt_from_dict(
            request.payload,
            source_system=request.source_system,
            allow_llm=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if request.allow_llm:
        warnings.extend(
            _try_attach_llm_suggestions(
                adapter_report=adapter_report,
                payload=request.payload,
                dialect_hint=request.dialect_hint,
                source_system=request.source_system,
                settings=settings,
                llm_mode=request.llm_mode,
            )
        )

    validated_uir = UIRDocument.model_validate(standard_uir.model_dump(mode="json"))
    route_report = (
        SchemaRouterService().route(
            validated_uir,
            adapter_report=adapter_report,
        )
        if request.route_schema
        else None
    )
    warnings.extend(adapter_report.warnings)
    return ExternalUIRConvertResponse(
        standard_uir=validated_uir,
        adapter_report=adapter_report,
        route_report=route_report,
        warnings=warnings,
        errors=adapter_report.errors,
    )


def _try_attach_llm_suggestions(
    *,
    adapter_report: AdapterReport,
    payload: dict[str, Any],
    dialect_hint: str | None,
    source_system: str,
    settings: Settings,
    llm_mode: str | None,
) -> list[str]:
    if not settings.external_uir_llm_enabled:
        return [
            "DeepSeek assistance is disabled or not configured. "
            "Deterministic adapter result is shown."
        ]
    if settings.external_uir_llm_provider != "deepseek" or llm_mode not in {None, "deepseek"}:
        return ["Unsupported External UIR LLM provider. Deterministic adapter result is shown."]

    try:
        report = ExternalUIRLLMSuggestionService(settings).suggest_adapter_mappings(
            payload_excerpt=payload,
            unknown_paths=_unknown_paths(payload),
            dialect_hint=dialect_hint,
            source_system=source_system,
        )
    except Exception as exc:  # noqa: BLE001 - LLM failures must not break deterministic conversion.
        return [f"DeepSeek assistance failed: {exc}"]

    adapter_report.assisted_suggestions = report.suggestions
    adapter_report.llm_used = True
    adapter_report.llm_auto_accepted_count = 0
    adapter_report.warnings.extend(report.warnings)
    return report.warnings


def _unknown_paths(payload: dict[str, Any]) -> list[str]:
    known = {"id", "title", "url", "chunks", "blocks", "items", "document"}
    paths = [f"payload.{key}" for key in sorted(payload) if key not in known]
    document = payload.get("document")
    if isinstance(document, dict):
        for key in sorted(document):
            if key not in {"docNo", "id", "name", "title", "source", "sections"}:
                paths.append(f"payload.document.{key}")
    return paths
