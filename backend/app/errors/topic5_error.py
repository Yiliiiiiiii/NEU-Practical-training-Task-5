from __future__ import annotations

import uuid
from typing import Any


class Topic5Error(RuntimeError):
    def __init__(
        self,
        *,
        error_code: str,
        stage: str,
        message: str,
        path: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
        trace_id: str | None = None,
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.stage = stage
        self.path = path
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        self.trace_id = trace_id or uuid.uuid4().hex
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "stage": self.stage,
            "path": self.path,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
            "trace_id": self.trace_id,
        }
