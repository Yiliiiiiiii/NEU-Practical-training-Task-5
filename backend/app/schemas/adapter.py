from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class AdapterCapability(StrictBaseModel):
    adapter_id: str
    adapter_version: str
    supported_dialects: list[str]
    source_systems: list[str]
    supports_tables: bool = True
    supports_sections: bool = True
    supports_pages: bool = False
    supports_bbox: bool = False
    requires_llm: bool = False
    description: str


class AdapterSelectionItem(StrictBaseModel):
    adapter_id: str
    confidence: float


class SelectedAdapter(StrictBaseModel):
    adapter_id: str | None
    confidence: float
    alternatives: list[AdapterSelectionItem] = Field(default_factory=list)
    review_required: bool = False
    error: str | None = None


class AdapterListResponse(StrictBaseModel):
    items: list[AdapterCapability]


class AdapterDetectRequest(StrictBaseModel):
    payload: dict[str, Any]
    source_system: str = "external"
    dialect_hint: str | None = "auto"
    options: dict[str, Any] = Field(default_factory=dict)


class AdapterDetectResponse(StrictBaseModel):
    selected_adapter: AdapterSelectionItem | None
    alternatives: list[AdapterSelectionItem] = Field(default_factory=list)
    review_required: bool = False
    error: str | None = None
