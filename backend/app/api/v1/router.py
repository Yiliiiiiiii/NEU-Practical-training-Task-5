from fastapi import APIRouter

from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.documents import router as documents_router
from app.api.v1.evaluation_center import router as evaluation_center_router
from app.api.v1.evaluation_reports import router as evaluation_reports_router
from app.api.v1.external_uir import router as external_uir_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.lineage import router as lineage_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.schema_drafts import router as schema_drafts_router
from app.api.v1.schemas import router as schemas_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.templates import router as templates_router
from app.api.v1.topic5 import router as topic5_router

api_router = APIRouter()
api_router.include_router(audit_logs_router)
api_router.include_router(documents_router)
api_router.include_router(evaluation_center_router)
api_router.include_router(evaluation_reports_router)
api_router.include_router(external_uir_router)
api_router.include_router(knowledge_router)
api_router.include_router(lineage_router)
api_router.include_router(reviews_router)
api_router.include_router(schema_drafts_router)
api_router.include_router(schemas_router)
api_router.include_router(tasks_router)
api_router.include_router(templates_router)
api_router.include_router(topic5_router)
