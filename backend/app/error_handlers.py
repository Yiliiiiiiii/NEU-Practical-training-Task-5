from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.schemas.api import ErrorBody, ErrorDetail, ErrorResponse


def _response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=[ErrorDetail.model_validate(item) for item in details or []],
        )
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def _http_code(status_code: int) -> str:
    if status_code in {400, 422}:
        return "VALIDATION_ERROR"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 409:
        return "TASK_STATE_ERROR"
    return "INTERNAL_ERROR" if status_code >= 500 else "VALIDATION_ERROR"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return _response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "path": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return _response(422, "VALIDATION_ERROR", "Invalid request", details)

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return _response(exc.status_code, _http_code(exc.status_code), message)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
        return _response(500, "INTERNAL_ERROR", "Internal server error")
