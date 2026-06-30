from fastapi import APIRouter

from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.documents import router as documents_router
from app.api.v1.evaluation_reports import router as evaluation_reports_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.schemas import router as schemas_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.templates import router as templates_router

api_router = APIRouter()
api_router.include_router(audit_logs_router)
api_router.include_router(documents_router)
api_router.include_router(evaluation_reports_router)
api_router.include_router(knowledge_router)
api_router.include_router(reviews_router)
api_router.include_router(schemas_router)
api_router.include_router(tasks_router)
api_router.include_router(templates_router)
