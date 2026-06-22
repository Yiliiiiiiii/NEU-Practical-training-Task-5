from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import Settings
from app.database import init_db
from app.error_handlers import register_error_handlers


def create_app(settings: Settings | None = None, init_database: bool | None = None) -> FastAPI:
    app_settings = settings or Settings()
    should_init_database = settings is None if init_database is None else init_database
    if should_init_database:
        init_db()

    app = FastAPI(title=app_settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-SHA256"],
    )
    register_error_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
