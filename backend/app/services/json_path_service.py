from __future__ import annotations

import re
from typing import Any

from app.schemas.common import StrictBaseModel
from app.schemas.conversion_assertions import validate_json_path

PATH_TOKEN_PATTERN = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)|\[(\d+)\]")


class PathResolution(StrictBaseModel):
    found: bool
    value: Any = None
    normalized_path: str
    error: str | None = None


class JsonPathService:
    def resolve(self, payload: Any, path: str) -> PathResolution:
        try:
            normalized_path = validate_json_path(path)
        except ValueError as exc:
            return PathResolution(
                found=False,
                normalized_path=path,
                error=str(exc),
            )

        current = payload
        for match in PATH_TOKEN_PATTERN.finditer(normalized_path[1:]):
            key, index_text = match.groups()
            if key is not None:
                if not isinstance(current, dict) or key not in current:
                    return PathResolution(found=False, normalized_path=normalized_path)
                current = current[key]
                continue

            index = int(index_text)
            if not isinstance(current, list) or index >= len(current):
                return PathResolution(found=False, normalized_path=normalized_path)
            current = current[index]

        return PathResolution(
            found=True,
            value=current,
            normalized_path=normalized_path,
        )
