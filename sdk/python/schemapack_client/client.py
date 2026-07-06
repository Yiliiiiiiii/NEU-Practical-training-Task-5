"""Synchronous SchemaPack HTTP client."""

from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx

from .models import JsonObject


class SchemaPackClientError(RuntimeError):
    """Raised for invalid or unsuccessful SchemaPack API responses."""


class SchemaPackClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"X-API-Key": api_key} if api_key else None
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def import_uir(self, uir: JsonObject) -> JsonObject:
        return self._json("POST", "/api/v1/documents/import", json={"uir": uir})

    def convert_external_uir(
        self,
        payload: JsonObject,
        *,
        source_system: str = "external",
        dialect_hint: str | None = None,
        route_schema: bool = True,
    ) -> JsonObject:
        return self._json(
            "POST",
            "/api/v1/external-uir/convert",
            json={
                "payload": payload,
                "source_system": source_system,
                "dialect_hint": dialect_hint,
                "route_schema": route_schema,
                "allow_llm": False,
                "dry_run": True,
            },
        )

    def import_external_uir(
        self,
        payload: JsonObject,
        *,
        source_system: str = "external",
        dialect_hint: str | None = None,
        route_schema: bool = True,
    ) -> JsonObject:
        return self._json(
            "POST",
            "/api/v1/external-uir/import",
            json={
                "payload": payload,
                "source_system": source_system,
                "dialect_hint": dialect_hint,
                "route_schema": route_schema,
                "allow_llm": False,
            },
        )

    def create_task(
        self,
        doc_id: str,
        schema_id: str,
        template_id: str,
        *,
        schema_version: str = "1.0.0",
        template_version: str = "1.0.0",
        options: JsonObject | None = None,
    ) -> JsonObject:
        return self._json(
            "POST",
            "/api/v1/tasks",
            json={
                "doc_id": doc_id,
                "schema_id": schema_id,
                "template_id": template_id,
                "schema_version": schema_version,
                "template_version": template_version,
                "options": options or {},
            },
        )

    def execute_task(self, task_id: str) -> JsonObject:
        return self._json("POST", f"/api/v1/tasks/{task_id}/execute")

    def download_package(self, task_id: str, output_path: str | Path) -> Path:
        response = self._client.get(f"/api/v1/tasks/{task_id}/package/download")
        self._raise_for_status(response)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)
        return output

    def list_schemas(self) -> JsonObject:
        return self._json("GET", "/api/v1/schemas")

    def list_adapters(self) -> JsonObject:
        return self._json("GET", "/api/v1/external-uir/adapters")

    def _json(self, method: str, path: str, **kwargs: Any) -> JsonObject:
        response = self._client.request(method, path, **kwargs)
        self._raise_for_status(response)
        payload = response.json()
        if not isinstance(payload, dict):
            raise SchemaPackClientError("SchemaPack API returned a non-object response")
        return payload

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = f"SchemaPack API request failed with HTTP {response.status_code}"
            try:
                payload = response.json()
                if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
                    detail = payload["detail"]
            except ValueError:
                pass
            raise SchemaPackClientError(detail) from exc
