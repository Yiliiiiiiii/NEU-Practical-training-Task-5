from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.mappings import router as mappings_router
from app.api.v1.reports import router as reports_router
from app.api.v1.schemas import router as schemas_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.templates import router as templates_router

api_router = APIRouter()
api_router.include_router(documents_router)
api_router.include_router(knowledge_router)
api_router.include_router(mappings_router)
api_router.include_router(reports_router)
api_router.include_router(schemas_router)
api_router.include_router(tasks_router)
api_router.include_router(templates_router)
