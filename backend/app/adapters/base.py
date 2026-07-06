from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from app.schemas.adapter import AdapterCapability
from app.schemas.common import StrictBaseModel
from app.schemas.external_uir import AdapterReport
from app.schemas.uir import UIRDocument


class AdapterInput(StrictBaseModel):
    payload: dict[str, Any]
    source_system: str = "unknown"
    dialect_hint: str | None = "auto"
    options: dict[str, Any] = Field(default_factory=dict)


class AdapterResult(StrictBaseModel):
    standard_uir: UIRDocument
    adapter_report: AdapterReport
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExternalUirAdapter(ABC):
    capability: AdapterCapability

    @abstractmethod
    def can_handle(self, adapter_input: AdapterInput) -> float:
        """Return confidence from 0.0 to 1.0."""

    @abstractmethod
    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        """Convert external UIR payload into a standard UIRDocument."""
