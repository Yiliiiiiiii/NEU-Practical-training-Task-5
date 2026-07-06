"""Scaffolded SchemaPack adapter. Review before registration."""

from app.adapters.base import AdapterInput, AdapterResult, ExternalUirAdapter
from app.schemas.adapter import AdapterCapability


class {{CLASS_NAME}}(ExternalUirAdapter):
    capability = AdapterCapability(
        adapter_id="{{ADAPTER_ID}}",
        adapter_version="{{ADAPTER_ID}}-adapter-v1",
        supported_dialects=["{{ADAPTER_ID}}"],
        source_systems=[],
        supports_tables=False,
        supports_sections=False,
        supports_pages=False,
        supports_bbox=False,
        requires_llm=False,
        description="Scaffolded adapter; implement and review before registration.",
    )

    def can_handle(self, adapter_input: AdapterInput) -> float:
        return 0.0

    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        raise NotImplementedError(
            "{{ADAPTER_ID}} conversion must be implemented before registration"
        )
