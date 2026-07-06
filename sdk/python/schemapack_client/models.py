"""Shared SDK type aliases."""

from typing import Any, TypedDict


JsonObject = dict[str, Any]


class TaskReference(TypedDict):
    task_id: str
    status: str
