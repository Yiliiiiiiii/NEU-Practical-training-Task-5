import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import Settings
from app.database import init_db
from app.errors import Topic5Error


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.settings = app_settings

    @app.exception_handler(Topic5Error)
    async def topic5_error_handler(_: Request, exc: Topic5Error) -> JSONResponse:
        return JSONResponse(exc.to_dict(), status_code=exc.status_code)

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        if request.url.path.startswith("/api/v1/topic5/convert"):
            content_length = request.headers.get("content-length")
            if (
                content_length is not None
                and content_length.isdigit()
                and int(content_length) > app_settings.topic5_max_request_bytes
            ):
                error = Topic5Error(
                    error_code="request_too_large",
                    stage="contract",
                    path="request",
                    message="Topic 5 request exceeds configured byte limit",
                    details={
                        "actual": int(content_length),
                        "maximum": app_settings.topic5_max_request_bytes,
                    },
                    status_code=413,
                )
                return JSONResponse(error.to_dict(), status_code=error.status_code)
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
