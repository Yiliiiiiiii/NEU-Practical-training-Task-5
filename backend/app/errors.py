from typing import Any


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(404, "NOT_FOUND", message)


class TaskStateError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "TASK_STATE_ERROR", message)


class SchemaInvalidError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "SCHEMA_INVALID", message)


class MappingReviewRequiredError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "MAPPING_REVIEW_REQUIRED", message)


class PackageNotReadyError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "PACKAGE_NOT_READY", message)
