import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import Settings
from app.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.settings = app_settings

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        if app_settings.api_key_auth_enabled and request.url.path.startswith("/api/v1"):
            supplied_key = request.headers.get("X-API-Key", "")
            allowed_keys = [
                key.strip()
                for key in app_settings.api_keys.split(",")
                if key.strip()
            ]
            if not supplied_key or not any(
                hmac.compare_digest(supplied_key, allowed_key)
                for allowed_key in allowed_keys
            ):
                return JSONResponse({"detail": "invalid or missing API key"}, status_code=401)
        return await call_next(request)

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
